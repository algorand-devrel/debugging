import json
from beaker import *
from pyteal import *


class DebugMe(Application):

    initialized = ApplicationStateValue(TealType.uint64, static=True)

    @external
    def bootstrap(self, asset: abi.Asset):
        return Seq(
            # Set initialized
            self.initialized.set(Int(1)),
            # Opt in
            self.send_asset(
                asset.asset_id(), Int(0), Global.current_application_address()
            ),
            Assert(Int(0), comment="lol gotcha")
        )

    @external
    def xfer(self, axfer: abi.AssetTransferTransaction, asset: abi.Asset):
        return Seq(
            Assert(self.initialized, comment="must be initialized"),
            self.send_asset(
                asset.asset_id(), axfer.get().asset_amount() / Int(2), Txn.sender()
            ),
        )

    @internal(TealType.none)
    def send_asset(self, id, amt, rcv):
        return Seq(
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: id,
                    TxnField.asset_amount: amt,
                    TxnField.asset_receiver: rcv,
                }
            ),
        )


if __name__ == "__main__":
    d = DebugMe()

    with open("app.teal", "w") as f:
        f.write(d.approval_program)

    with open("clear.teal", "w") as f:
        f.write(d.clear_program)

    with open("contract.json", "w") as f:
        f.write(json.dumps(d.contract.dictify()))

    with open("spec.json", "w") as f:
        f.write(json.dumps(d.application_spec()))
