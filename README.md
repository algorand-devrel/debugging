# Debugging Smart Contracts 

Debugging Smart Contracts is a critical part of development. 

This repo contains examples to demonstrate how a developer might approach debugging a Smart Contract using the Dryrun endpoint

Make sure you have the [sandbox](https://github.com/algorand/sandbox) installed and running locally

Documentation to help understanding the tools available is [here](https://developer.algorand.org/docs/get-details/dapps/smart-contracts/debugging/)

## Contracts

contracts/application.py - Beaker PyTeal Application
contracts/artifacts/approval.teal - The approval program generated from the Beaker application
contracts/artifacts/clear.teal - The clear program generated from the Beaker application
contracts/artifacts/contract.json - The ARC4 ABI Contract specification from the Beaker application
contracts/artifacts/DebugMe.json - The Beaker Application specification from the Beaker application

## Flow

### Setup

Clone this repo down

```sh
git clone git@github.com:algorand-devrel/debugging.git
cd debugging
```

Create a python virtual environment and install `beaker-pyteal` so we can rebuild the beaker application
```sh
$ python -m venv .venv
$ source .venv/bin/activate
(.venv)$ pip install beaker-pyteal
```

### Python SDK

If using python, keep the virtual environment sourced and cd into the python directory then run the file `main.py`

```sh
(.venv)$ cd py
(.venv)$ python main.py
```

Proceed to [debugging](#debugging)

### JS SDK

### Go SDK

### Java SDK

### Goal/Tealdbg



### Debugging

If you need to modify the contract logic, make sure the virtualenv is active and run:
```
(.venv)$ cd contracts
(.venv)$ python application.py
```
This will overwrite the teal programs and contract json file. 


Follow this algorithm to debug:
```
While Broken:

    Create a transaction group
    
    Execute it

    If broken: 
        Create DryrunRequest object using SDK method

        Send DryrunRequest to algod

        Parse DryrunResponse object

        Print Stack Trace

        Inspect it

        Try a fixing something
```

happy hacking :)