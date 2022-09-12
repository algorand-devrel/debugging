import algosdk from 'algosdk'
import * as bkr from 'beaker-ts'
import {getApprovalProgram, getClearProgram, getContract, createApp, createAsset} from './utils'

(async function(){
    const client = bkr.sandbox.getAlgodClient()
    const accts = await bkr.sandbox.getAccounts()
    const acct = accts.pop()
    if(acct === undefined) return

    // Get Programs and map 
    const [approvalSrc, approvalBin, approvalMap] = await getApprovalProgram(client)
    const [, clearBin, ] = await getClearProgram(client)

    // Get contract
    const contract = await getContract()

    console.log("Got contract")

    // Create app
    const [appId, appAddr] = await createApp(client, acct.addr, acct.privateKey, approvalBin, clearBin)

    console.log(`Created app: ${appId} (${appAddr})`)

    // Create ASA
    const asaId = await createAsset(client, acct.addr, acct.privateKey)
    console.log(`Created asset: ${asaId}`)

    // Get sp
    const sp = await client.getTransactionParams().do()
    sp.flatFee = true
    sp.fee = 2000

    // Bootstrap the contract to 
    let atc = new algosdk.AtomicTransactionComposer() 
    atc.addMethodCall({
        appID: appId, 
        sender: acct.addr,
        signer: acct.signer,
        suggestedParams: sp,
        method: contract.getMethodByName("bootstrap"),
        methodArgs:[asaId]
    })
    try {
        await atc.execute(client, 4)
    }catch(e){
        console.error(e)
    }

    // Transfer some of the asset to the contract
    atc = new algosdk.AtomicTransactionComposer()
    const axfer = algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
        from: acct.addr,
        to: appAddr,
        assetIndex: asaId,
        amount: 10,
        suggestedParams: sp,
    })
    atc.addMethodCall({
        appID: appId, 
        sender: acct.addr,
        signer: acct.signer,
        suggestedParams: sp,
        method: contract.getMethodByName("transfer"),
        methodArgs:[{txn: axfer, signer: acct.signer}, asaId]
    })

    try {
        await atc.execute(client, 4)
    }catch(e){
        console.error(e)
    }

    // Call withdraw
    atc = new algosdk.AtomicTransactionComposer()
    atc.addMethodCall({
        appID: appId, 
        sender: acct.addr,
        signer: acct.signer,
        suggestedParams: sp,
        method: contract.getMethodByName("withdraw"),
        methodArgs:[asaId]
    })
    try{
        await atc.execute(client, 4)
    }catch(e){
        console.error(e)
    }


})()