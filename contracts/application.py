import os
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
                comment="Incorrect asset",
            ),
            Assert(
                axfer.get().asset_receiver() == self.address,
                comment="Receiver should be application address",
            ),
            self.send_asset(
                asset.asset_id(), axfer.get().asset_amount() - Int(10), Txn.sender()
            ),
        )

    # TODO: this call will fail with invalid asset reference because the
    # asset argument is a uint not an asset reference.
    # Change the method signature to specify that it wants an asset reference instead
    # of the Uint64 and get its id using `.asset_id` instead of `.get`.
    # See above for examples.

    # Create group transaction to send asset and call method
    #     If you need to modify the contract logic, make sure the virtualenv is active and run:
    # ```
    # (.venv)$ cd contracts
    # (.venv)$ python application.py
    # ```
    # This will overwrite the teal programs and contract json file.

    @external
    def withdraw(self, asset: abi.Uint64):
        """withdraw allows 1 unit of the asset passed to be sent to the caller

        Args:
            asset: The asset we're set up to handle
        """
        return self.send_asset(asset.get(), Int(1), Txn.sender())

        
    # @external    
    # def withdraw(self, asset: abi.Asset):
    #     """withdraw allows 1 unit of the asset passed to be sent to the caller
    #     Args:
    #         asset: The asset we're set up to handle
    #     """
    #     return self.send_asset(asset.asset_id(), Int(1), Txn.sender())
    
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
