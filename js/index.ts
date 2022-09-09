import algosdk from 'algosdk'
import * as bkr from 'beaker-ts'

(async function(){
    const client = bkr.sandbox.getAlgodClient()
    const accts = await bkr.sandbox.getAccounts()
    const acct = accts.pop()
    if(acct === undefined) return

    const sp = await client.getTransactionParams().do()

    // Show that current round suggested > what we have set
    if(sp.firstRound<1) return

    sp.firstRound = 0
    sp.lastRound = 1
    
    const pay = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
        from: acct.addr,
        suggestedParams: sp,
        to: acct.addr,
        amount: 0
    })

    try {
        console.log("Trying to send it")
        await client.sendRawTransaction(pay.signTxn(acct.privateKey)).do()
        console.log(await algosdk.waitForConfirmation(client, pay.txID(), 4))
    }catch(e){
        console.log("caught it")
    }

})()