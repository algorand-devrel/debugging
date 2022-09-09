import base64
from algosdk.v2client import algod
from algosdk.dryrun_results import DryrunResponse
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

    # Create group txn
    sp = algod_client.suggested_params()
    sp.flat_fee = True
    sp.fee = 3000

    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id,
        contract.get_method_by_name("bootstrap"),
        acct.address,
        sp,
        signer=acct.signer,
        method_args=[asa_id],
    )
    axfer = TransactionWithSigner(
        txn=transaction.AssetTransferTxn(acct.address, sp, app_addr, 10, asa_id),
        signer=acct.signer,
    )

    atc.add_method_call(
        app_id,
        contract.get_method_by_name("transfer"),
        acct.address,
        sp,
        signer=acct.signer,
        method_args=[axfer, asa_id],
    )

    try:
        atc.execute(algod_client, 4)
    except Exception as e:
        print(e)
        le = LogicException(e, approval_program, approval_map)
        print(le.trace(10))


def create_dryrun():
    pass
    # signed = atc.gather_signatures()
    # drr = transaction.create_dryrun(client, signed)
    # dr = client.dryrun(drr)

    # dryrun_result = DryrunResponse(dr)
    # for txn in dryrun_result.txns:
    #    if txn.app_call_rejected():
    #        error_msg = txn.app_call_messages[-1]
    #        le = LogicException(error_msg, approval_program, approval_map)
    #        print(le.__dict__)
    #        print(txn.app_trace(StackPrinterConfig(max_value_width=10)))


if __name__ == "__main__":
    main()
