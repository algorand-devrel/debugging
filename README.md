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

If using the JS SDK, cd into the `js` directory and install the required modules
```
cd `js`
npm install
```

Then run the demo program
```
npm run demo
```

Proceed to [debugging](#debugging)

### Go SDK

TODO
### Java SDK

TODO

### Goal/Tealdbg

When using the `goal` and `tealdbg` process each step is contained within its own file. You may debug the step by specifying an argument after the script e.g. `./0_deploy debug`. Note this uses `sandbox` by default, but if you have a node running locally modify the code to remove the variable `SB`.

```sh
$ cd sh
$ ./0_deploy.sh
$ ./0_deploy.sh debug
$ ./1_bootstrap.sh
$ ./1_bootstrap.sh debug
$ ./2_transfer.sh
$ ./2_transfer.sh debug
$ ./3_withdraw.sh
$ ./3_withdraw.sh debug
```

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
