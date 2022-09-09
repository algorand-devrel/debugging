import json
from operator import methodcaller
from algosdk.v2client import *
from algosdk.dryrun_results import *
from algosdk.atomic_transaction_composer import *
from algosdk.future import transaction
from algosdk.source_map import SourceMap
from util import create_app, create_asa
from beaker import sandbox
from beaker.client.logic_error import parse_logic_error, LogicException


def compile(client: algod.AlgodClient, program: str) -> tuple[bytes, SourceMap]:
    result = client.compile(program, source_map=True)
    program_binary = base64.b64decode(result["result"])
    src_map = SourceMap(result["sourcemap"])
    return [program_binary, src_map]


def get_approval_program(client: algod.AlgodClient) -> tuple[str, bytes, SourceMap]:
    with open("../contracts/app.teal", "r") as f:
        approval_program = f.read()
    approval_bin, approval_map = compile(client, approval_program)
    return approval_program, approval_bin, approval_map


def get_clear_program(client: algod.AlgodClient) -> tuple[str, bytes, SourceMap]:
    with open("../contracts/clear.teal", "r") as f:
        clear_program = f.read()
    clear_bin, clear_map = compile(client, clear_program)
    return clear_program, clear_bin, clear_map


def get_contract() -> abi.Contract:
    with open("../contracts/contract.json", "r") as f:
        return abi.Contract.from_json(f.read())


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
        contract.get_method_by_name("xfer"),
        acct.address,
        sp,
        signer=acct.signer,
        method_args=[axfer, asa_id],
    )

    try:
        atc.execute(algod_client, 4)
    except Exception as e:
        raise LogicException(e, approval_program, approval_map)

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
