from pyteal import *


def sig():
    return Cond(
        [Arg(0) == Bytes("succeed"), Approve()], 
        [Int(1), Reject()]
    )


def get_sig() -> str:
    return compileTeal(sig(), mode=Mode.Signature, version=6)


if __name__ == "__main__":
    with open("lsig.teal", "w") as f:
        f.write(get_sig())
