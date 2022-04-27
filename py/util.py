from algosdk.v2client import algod
from algosdk.kmd import KMDClient
from algosdk.future import transaction
import json
import base64


def get_config():
    # TODO make full path not relative
    with open("../config.json", "r") as f:
        return json.load(f)


def compile_program(client, program):
    # Read in approval teal source && compile
    result = client.compile(program)
    return base64.b64decode(result["result"])


def get_programs(client, config):
    approval_path = "../" + config["contracts"]["approval"]
    clear_path = "../" + config["contracts"]["clear"]
    lsig_path = "../" + config["contracts"]["lsig"]

    with open(approval_path, "r") as f:
        approval = compile_program(client, f.read())

    with open(clear_path, "r") as f:
        clear = compile_program(client, f.read())

    with open(lsig_path, "r") as f:
        lsig = compile_program(client, f.read())

    return approval, clear, lsig


def get_client(config):
    token = config["algod"]["token"]
    address = "{}:{}".format(config["algod"]["host"], config["algod"]["port"])
    return algod.AlgodClient(token, address)


def get_accounts(config):
    token = config["kmd"]["token"]
    address = config["kmd"]["address"]
    name = config["kmd"]["name"]
    password = config["kmd"]["password"]

    kmd = KMDClient(token, address)
    wallets = kmd.list_wallets()

    walletID = None
    for wallet in wallets:
        if wallet["name"] == name:
            walletID = wallet["id"]
            break

    if walletID is None:
        raise Exception("Wallet not found: {}".format(name))

    walletHandle = kmd.init_wallet_handle(walletID, password)

    try:
        addresses = kmd.list_keys(walletHandle)
        privateKeys = [
            kmd.export_key(walletHandle, password, addr) for addr in addresses
        ]
        kmdAccounts = [(addresses[i], privateKeys[i]) for i in range(len(privateKeys))]
    finally:
        kmd.release_wallet_handle(walletHandle)

    return kmdAccounts


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
) -> int:
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
