import base64
from algosdk.v2client import algod
from algosdk.dryrun_results import DryrunResponse, StackPrinterConfig
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.future import transaction
from util import (
    create_app,
    create_asa,
    get_approval_program,
    get_clear_program,
    get_contract,
)
from beaker import sandbox
from beaker.client.logic_error import LogicException


def main():
    # setup
    algod_client = sandbox.clients.get_algod_client()
    acct = sandbox.kmd.get_accounts().pop()

    approval_program, approval_bin, approval_map = get_approval_program(algod_client)
    _, clear_bin, _ = get_clear_program(algod_client)

    contract = get_contract()

    app_id, app_addr = create_app(
        algod_client,
        acct.address,
        acct.private_key,
        approval_bin,
        clear_bin,
        transaction.StateSchema(1, 0),
        transaction.StateSchema(0, 0),
    )

    asa_id = create_asa(
        algod_client, acct.address, acct.private_key, "tmp_asset", "tmp", 10000, 0
    )

    sp = algod_client.suggested_params()

    # TODO: Need to cover fees for the inner transaction (uncomment these lines)
    # sp.flat_fee = True # Tell the SDK we know exactly what our fee should be
    # sp.fee = 2000 # Cover 2 transaction (outer + inner)

    # Create transaction to bootstrap application
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id,
        contract.get_method_by_name("bootstrap"),
        acct.address,
        sp,
        signer=acct.signer,
        method_args=[asa_id],
    )

    try:
        atc.execute(algod_client, 4)
    except Exception as e:
        le = LogicException(e, approval_program, approval_map)
        print(
            f"A Logic Exception was encountered: '{le.msg[:15]}...'\n\t{le.trace()}\n"
        )
        perform_dryrun(atc, algod_client)
        return

    # Create group transaction to send asset and call method
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id,
        contract.get_method_by_name("transfer"),
        acct.address,
        sp,
        signer=acct.signer,
        method_args=[
            TransactionWithSigner(
                txn=transaction.AssetTransferTxn(
                    acct.address, sp, app_addr, 10, asa_id
                ),
                signer=acct.signer,
            ),
            asa_id,
        ],
    )
    try:
        atc.execute(algod_client, 4)
    except Exception as e:
        le = LogicException(e, approval_program, approval_map)
        print(
            f"A Logic Exception was encountered: '{le.msg[:15]}...'\n\t{le.trace()}\n"
        )
        perform_dryrun(atc, algod_client)
        return


def perform_dryrun(atc: AtomicTransactionComposer, client: algod.AlgodClient):
    signed = atc.gather_signatures()
    drr = transaction.create_dryrun(client, signed)
    dryrun_result = DryrunResponse(client.dryrun(drr))
    for txn in dryrun_result.txns:
        if txn.app_call_rejected():
            print(txn.app_trace(StackPrinterConfig(max_value_width=30)))


if __name__ == "__main__":
    main()
