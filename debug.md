This repository is meant to foce the developer through a number of common steps involved in debugging in order to familiarize themselves with the tools available. 

The contract and the SDK usage that calls the contract include bugs that should be straight forward to debug.

Namely the included bugs are:

- Fee too small for 0 fee inner transactions (Set flat fee and increase fee on suggested parameters)
- Invalid asset reference (Passing 0 for asset id should fail with invalid asset)
- Math undeflow (9-10 would result negative, update transaction to send >=10 units)
- Invalid parameter declaration leading to unavailable foreign reference (Update contract to require abi.Asset instead of abi.Uint64)

