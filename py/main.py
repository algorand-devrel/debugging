from algosdk.v2client import *
from algosdk.dryrun_results import *
from algosdk.future import transaction
from util import *


def main():
    config = get_config()
    client = get_client(config)
    accts = get_accounts(config)

    addr, pk = accts[0]

    # Setup
    approval, clear, _ = get_programs(client, config)
    app_id, app_addr = create_app(
        client,
        addr,
        pk,
        approval,
        clear,
        transaction.StateSchema(0, 1),
        transaction.StateSchema(0, 0),
    )
    asa_id = create_asa(client, addr, pk, "testasa", "tasa", 100, 0)

    # Create group txn
    sp = client.suggested_params()

    bootstrap = transaction.ApplicationCallTxn(
        addr,
        sp,
        app_id,
        transaction.OnComplete.NoOpOC,
        app_args=["bootstrap"],
        foreign_assets=[asa_id],
    )
    asset_xfer = transaction.AssetTransferTxn(addr, sp, app_addr, 10, asa_id)
    app_xfer = transaction.ApplicationCallTxn(
        addr,
        sp,
        app_id,
        transaction.OnComplete.NoOpOC,
        app_args=["xfer", "Asdfa"],
        foreign_assets=[asa_id],
    )

    signed = [
        txn.sign(pk)
        for txn in transaction.assign_group_id([bootstrap, asset_xfer, app_xfer])
    ]

    # Send it to the real network
    #txid = client.send_transactions(signed)
    #print("Result: {}".format(transaction.wait_for_confirmation(client, txid, 2)))
    #return

    # Dryrun it
    drr = transaction.create_dryrun(client, signed)
    dr = client.dryrun(drr)

    dryrun_result = DryrunResponse(dr)

    for txn in dryrun_result.txns:
        if txn.app_call_rejected():
            print(txn.app_trace(StackPrinterConfig(max_value_width=0)))


if __name__ == "__main__":
    main()
