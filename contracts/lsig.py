from pyteal import *
from beaker import *


class Lsig(LogicSignature):
    def evaluate(self):
        return Cond([Arg(0) == Bytes("succeed"), Approve()], [Int(1), Reject()])


if __name__ == "__main__":
    lsig = Lsig()

    def get_sig() -> str:
        return compileTeal(lsig.program, mode=Mode.Signature, version=6)

    with open("lsig.teal", "w") as f:
        f.write(get_sig())
