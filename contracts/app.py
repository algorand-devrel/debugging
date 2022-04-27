from ensurepip import bootstrap
from pyteal import *

args = Txn.application_args

abi_match = lambda selector: args[0] == selector

on_complete = lambda oc: Txn.on_completion() == oc

isCreate = Txn.application_id() == Int(0)
isOptIn = on_complete(OnComplete.OptIn)
isClear = on_complete(OnComplete.ClearState)
isClose = on_complete(OnComplete.CloseOut)
isUpdate = on_complete(OnComplete.UpdateApplication)
isDelete = on_complete(OnComplete.DeleteApplication)
isNoOp = on_complete(OnComplete.NoOp)

key = Bytes("test")
val = Bytes("dope")

@Subroutine(TealType.uint64)
def bootstrap():
    return Seq(
        App.globalPut(key, val),
        send_asset(Txn.assets[0], Int(0), Global.current_application_address()),
        Int(1)
    )

@Subroutine(TealType.uint64)
def xfer():
    return Seq(
        If(Txn.application_args.length() == Int(1), Assert(App.globalGet(key) == val)),
        send_asset(Txn.assets[0], Gtxn[Txn.group_index() - Int(1)].asset_amount() / Int(2), Txn.sender()),
        Int(1)
    )


@Subroutine(TealType.none)
def send_asset(id, amt, rcv):
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: id,
            TxnField.asset_amount: amt,
            TxnField.asset_receiver: rcv,
        }),
        InnerTxnBuilder.Submit(),
    )


def approval():

    router = Cond(
        [Txn.application_args[0] == Bytes("bootstrap"), bootstrap()],
        [Txn.application_args[0] == Bytes("xfer"), xfer()]
    )

    return Cond(
        [isCreate, Approve()],
        [isOptIn, Approve()],
        [isClear, Approve()],
        [isClose, Approve()],
        [isUpdate, Approve()],
        [isDelete, Approve()],
        [isNoOp, Return(router)]
    )


def clear():
    return Approve()


def get_approval():
    return compileTeal(approval(), mode=Mode.Application, version=6)


def get_clear():
    return compileTeal(clear(), mode=Mode.Application, version=6)


if __name__ == "__main__":
    with open("app.teal", "w") as f:
        f.write(get_approval())

    with open("clear.teal", "w") as f:
        f.write(get_clear())
