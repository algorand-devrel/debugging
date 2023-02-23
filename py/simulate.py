from algosdk.v2client import algod
from algosdk.dryrun_results import DryrunResponse, StackPrinterConfig
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk import transaction
from util import (
    create_app,
    create_asa,
    get_approval_program,
    get_clear_program,
    get_contract,
)
from beaker import sandbox
import os


def main():
    # setup
    algod_client = sandbox.clients.get_algod_client()
    acct = sandbox.kmd.get_accounts().pop()

    _, approval_bin, _ = get_approval_program(algod_client)
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
    # sp.flat_fee = True  # Tell the SDK we know exactly what our fee should be
    # sp.fee = 2000  # Cover 2 transaction (outer + inner)

    # Create transaction to bootstrap application
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id,
        contract.get_method_by_name("bootstrap"),
        acct.address,
        sp,
        signer=acct.signer,
        # TODO: the asset id should be passed
        method_args=[0],
        # method_args=[asa_id],
    )

    try:
        atc.execute(algod_client, 4)
    except Exception as e:
        perform_simulate(atc, algod_client)
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
                # TODO: make this not fail
                txn=transaction.AssetTransferTxn(acct.address, sp, app_addr, 9, asa_id),
                # txn=transaction.AssetTransferTxn(acct.address, sp, app_addr, 10, asa_id),
                signer=acct.signer,
            ),
            asa_id,
        ],
    )
    try:
        atc.execute(algod_client, 4)
    except Exception as e:
        perform_simulate(atc, algod_client)
        return

    # Create group transaction to send asset and call method
    # See TODO in contracts/application.py
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id,
        contract.get_method_by_name("withdraw"),
        acct.address,
        sp,
        signer=acct.signer,
        method_args=[asa_id],
    )
    try:
        atc.execute(algod_client, 4)
    except Exception as e:
        perform_simulate(atc, algod_client)
        return


def perform_simulate(atc: AtomicTransactionComposer, client: algod.AlgodClient):
    r = atc.simulate(client).txn_groups[0]
    print(f"Failure Message: {r.failure_message}")
    print(f"Failed Transaction: {r.failed_at[0]}")

    for i, res in enumerate(r.txn_results):

        print(f"Txn {i} Results:")
        for key, value in res.result.__dict__.items():
            if key != "txn":
                print(f"  {key}: {value}")
            else:
                print(f"  txn: {value.transaction.get_txid()}")
                print(f"  txn_type: {value.transaction.type}")
                print(f"  txn_fee: {value.transaction.fee}")


if __name__ == "__main__":
    main()
