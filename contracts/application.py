from beaker import *
from pyteal import *


class DebugMe(Application):

    asset_id = ApplicationStateValue(TealType.uint64, static=True)

    @external
    def bootstrap(self, asset: abi.Asset):
        """bootstraps the application to set the initialized flag and opt into the asset passed

        Args:
            asset: Asset this contract should opt in to

        """
        return Seq(
            # Set asset id we intend to opt in to
            self.asset_id.set(asset.asset_id()),
            # Opt application account in to asset
            self.send_asset(asset.asset_id(), Int(0), self.address),
        )

    @external
    def transfer(self, axfer: abi.AssetTransferTransaction, asset: abi.Asset):
        """transfers the amount sent, less 10 units, back to the sender

        Args:
            axfer: The asset transfer transaction to the contract
            asset: The asset that this contract has opted in to

        """
        return Seq(
            Assert(
                asset.asset_id() == self.asset_id, 
                axfer.get().xfer_asset() == self.asset_id,
                comment="Incorrect asset"
            ),
            Assert(
                axfer.get().asset_receiver() == self.address,
                comment="Receiver should be application address",
            ),
            self.send_asset(
                asset.asset_id(), axfer.get().asset_amount() - Int(10), Txn.sender()
            ),
        )

    @internal(TealType.none)
    def send_asset(self, id, amt, rcv):
        """send asset handles executing the inner transaction to send an asset"""
        return InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: id,
                TxnField.asset_amount: amt,
                TxnField.asset_receiver: rcv,
                TxnField.fee: Int(0),
            }
        )


if __name__ == "__main__":
    DebugMe().dump("./artifacts")
