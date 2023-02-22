from algosdk.v2client import algod
from algosdk.kmd import KMDClient
from algosdk import transaction
from algosdk.source_map import SourceMap
from algosdk import abi
import base64


def compile(client: algod.AlgodClient, program: str) -> tuple[bytes, SourceMap]:
    result = client.compile(program, source_map=True)
    program_binary = base64.b64decode(result["result"])
    src_map = SourceMap(result["sourcemap"])
    return [program_binary, src_map]


artifact_path = "../contracts/artifacts/"


def get_approval_program(client: algod.AlgodClient) -> tuple[str, bytes, SourceMap]:
    with open(artifact_path + "approval.teal", "r") as f:
        approval_program = f.read()
    approval_bin, approval_map = compile(client, approval_program)
    return approval_program, approval_bin, approval_map


def get_clear_program(client: algod.AlgodClient) -> tuple[str, bytes, SourceMap]:
    with open(artifact_path + "clear.teal", "r") as f:
        clear_program = f.read()
    clear_bin, clear_map = compile(client, clear_program)
    return clear_program, clear_bin, clear_map


def get_contract() -> abi.Contract:
    with open(artifact_path + "contract.json", "r") as f:
        return abi.Contract.from_json(f.read())


def create_asa(
    client: algod.AlgodClient,
    addr: str,
    pk: str,
    name: str,
    unit_name: str,
    total: int,
    decimals: int,
) -> int:
    # Get suggested params from network
    sp = client.suggested_params()

    # Create the transaction
    create_txn = transaction.AssetCreateTxn(
        addr,
        sp,
        total,
        decimals,
        False,
        unit_name=unit_name,
        asset_name=name,
    )

    # Sign it
    signed_txn = create_txn.sign(pk)

    # Send it
    txid = client.send_transaction(signed_txn)

    # Wait for the result so we can return the asset id
    result = transaction.wait_for_confirmation(client, txid, 4)

    return result["asset-index"]


def create_app(
    client: algod.AlgodClient,
    addr: str,
    pk: str,
    app_bytes: bytes,
    clear_bytes: bytes,
    global_schema,
    local_schema,
) -> tuple[int, str]:
    # Get suggested params from network
    sp = client.suggested_params()

    # Create the transaction
    create_txn = transaction.ApplicationCreateTxn(
        addr,
        sp,
        0,
        app_bytes,
        clear_bytes,
        global_schema,
        local_schema,
    )

    # Sign it
    signed_txn = create_txn.sign(pk)

    # Ship it
    txid = client.send_transaction(signed_txn)

    # Wait for the result so we can return the app id
    result = transaction.wait_for_confirmation(client, txid, 4)
    app_id = result["application-index"]
    app_addr = transaction.logic.get_application_address(app_id)

    # Make sure the app address is funded with at least min balance
    ptxn = transaction.PaymentTxn(addr, sp, app_addr, int(1e8))
    txid = client.send_transaction(ptxn.sign(pk))
    transaction.wait_for_confirmation(client, txid, 4)

    return app_id, app_addr


def update_app(
    client: algod.AlgodClient, app_id: int, addr: str, pk: str, get_approval, get_clear
) -> int:
    # Get suggested params from network
    sp = client.suggested_params()

    # Read in approval teal source && compile
    app_result = client.compile(get_approval())
    app_bytes = base64.b64decode(app_result["result"])

    # Read in clear teal source && compile
    clear_result = client.compile(get_clear())
    clear_bytes = base64.b64decode(clear_result["result"])

    # Create the transaction
    create_txn = transaction.ApplicationUpdateTxn(
        addr,
        sp,
        app_id,
        app_bytes,
        clear_bytes,
    )

    # Sign it
    signed_txn = create_txn.sign(pk)

    # Ship it
    txid = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, txid, 4)


def delete_app(client: algod.AlgodClient, app_id: int, addr: str, pk: str):
    # Get suggested params from network
    sp = client.suggested_params()

    # Create the transaction
    txn = transaction.ApplicationDeleteTxn(addr, sp, app_id)

    # sign it
    signed = txn.sign(pk)

    # Ship it
    txid = client.send_transaction(signed)

    return transaction.wait_for_confirmation(client, txid, 4)


def destroy_apps(client: algod.AlgodClient, addr: str, pk: str):
    acct = client.account_info(addr)

    # Delete all apps created by this account
    for app in acct["created-apps"]:
        delete_app(client, app["id"], addr, pk)
