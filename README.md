# Debugging

Debugging Smart Contracts is a critical part of development. 

This repo contains examples to demonstrate how a developer might approach debugging a Smart Contract using the Dryrun endpoint

Make sure you have the [sandbox](https://github.com/algorand/sandbox) installed and running locally


## Contracts

app.teal - The approval program for the app we wish to debug
clear.teal - The clear program for the app we wish to debug
lsig.teal - The smart signature we wish to debug

## Flow

### Setup

Create application

Fund app address

Fund lsig address

### Debug

While Broken:

    Create a transaction group

    Create DryrunRequest object using SDK method

    Send DryrunRequest to algod

    Parse DryrunResponse object

    Print Stack Trace

    Inspect it

    If broken, fix 
    Else done!


happy hacking :)