import algosdk, { SourceMap } from "algosdk";
import fs from 'fs'

const artifactPath = "../contracts/artifacts/"

async function compileProgram(client: algosdk.Algodv2, buff: Buffer): Promise<[Uint8Array, SourceMap]> {
    const result = await client.compile(new Uint8Array(buff)).sourcemap(true).do()
    const bin = new Uint8Array(Buffer.from(result["result"], "base64"))
    const sm = new SourceMap(result["sourcemap"])
    return [bin, sm]
}

export async function getApprovalProgram(client: algosdk.Algodv2): Promise<[string, Uint8Array, SourceMap]>{
    const buff = fs.readFileSync(artifactPath + "approval.teal")
    const [bin, sm] = await compileProgram(client, buff)
    return [buff.toString('utf-8'), bin, sm]
}

export async function getClearProgram(client: algosdk.Algodv2): Promise<[string, Uint8Array, SourceMap]>{
    const buff = fs.readFileSync(artifactPath + "clear.teal")
    const [bin, sm] = await compileProgram(client, buff)
    return [buff.toString('utf-8'), bin, sm]
}

export async function getContract(): Promise<algosdk.ABIContract> {
    const buff = fs.readFileSync(artifactPath + "contract.json")
    return new algosdk.ABIContract(JSON.parse(buff.toString()))
}

export async function createApp(client: algosdk.Algodv2, addr: string, privateKey: Buffer, approval: Uint8Array, clear: Uint8Array): Promise<[number, string]> {
    const sp = await client.getTransactionParams().do()
    const txn = algosdk.makeApplicationCreateTxnFromObject({
        from: addr,
        suggestedParams: sp,
        onComplete: algosdk.OnApplicationComplete.NoOpOC,
        approvalProgram: approval,
        clearProgram: clear,
        numLocalInts: 0,
        numLocalByteSlices: 0,
        numGlobalInts: 1,
        numGlobalByteSlices: 0
    })
    await client.sendRawTransaction(txn.signTxn(privateKey)).do()
    const result = await algosdk.waitForConfirmation(client, txn.txID(), 4)
    const appId = result["application-index"]
    const address = algosdk.getApplicationAddress(appId)


    // Give the app some algos so it can opt in to the asset
    const ptxn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
        from: addr,
        to: address,
        amount: 1e8,
        suggestedParams: sp,
    })
    await client.sendRawTransaction(ptxn.signTxn(privateKey)).do()


    return [appId,address]
}

export async function createAsset(client: algosdk.Algodv2, addr: string, privateKey: Buffer): Promise<number> {
    const sp = await client.getTransactionParams().do()

    const txn = algosdk.makeAssetCreateTxnWithSuggestedParamsFromObject({
        from: addr,
        suggestedParams: sp,
        total: 100000,
        decimals: 0,
        assetName:"tmp_asset",
        unitName:"tmp",
        defaultFrozen: false
    })

    await client.sendRawTransaction(txn.signTxn(privateKey)).do()
    const result = await algosdk.waitForConfirmation(client, txn.txID(), 4)
    const assetId = result["asset-index"]
    return assetId
}