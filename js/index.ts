import algosdk from "algosdk";
import * as bkr from "beaker-ts";
import {
  getApprovalProgram,
  getClearProgram,
  getContract,
  createApp,
  createAsset,
} from "./utils";

//const LOGIC_ERROR = /TransactionPool.Remember: transaction ([A-Z0-9]+): logic eval error: (.*). Details: pc=([0-9]+), opcodes=.*/
//
//interface LogicErrorDetails {
//    txId: string
//    pc: number
//    msg: string
//}
//
//export function parseLogicError(errMsg: string): LogicErrorDetails {
//    const res = LOGIC_ERROR.exec(errMsg)
//    console.log(res)
//    if(res === null || res.length<=3) return {} as LogicErrorDetails
//
//    return {
//        txId: res[1],
//        msg: res[2],
//        pc: parseInt(res[3]?res[3]:"0"),
//    } as LogicErrorDetails
//}



(async function () {
  const client = bkr.sandbox.getAlgodClient();
  const accts = await bkr.sandbox.getAccounts();
  const acct = accts.pop();
  if (acct === undefined) return;

  // Get Programs and map
  const [approvalSrc, approvalBin, approvalMap] = await getApprovalProgram(
    client
  );
  const [, clearBin] = await getClearProgram(client);

  // Util function to wrap the error returned from a call 
  // to algod in a `LogicError` with sourcemap and parsed
  // exception. Defined here so we can capture the approvalSrc/Map
  function wrapLogicError(e: Error): bkr.LogicError {
    return new bkr.LogicError(
      bkr.parseLogicError(e.message),
      approvalSrc.split("\n"),
      approvalMap
    );
  }

  // Get contract
  const contract = await getContract();

  // Create app
  const [appId, appAddr] = await createApp(
    client,
    acct.addr,
    acct.privateKey,
    approvalBin,
    clearBin
  );
  console.log(`Created app: ${appId} (${appAddr})`);

  // Create ASA
  const asaId = await createAsset(client, acct.addr, acct.privateKey);
  console.log(`Created asset: ${asaId}`);

  // Get sp
  const sp = await client.getTransactionParams().do();
  // TODO: uncomment these to cover the fee for inner transactions
  //sp.flatFee = true;
  //sp.fee = 2000;

  // Bootstrap the contract to
  let atc = new algosdk.AtomicTransactionComposer();
  atc.addMethodCall({
    appID: appId,
    sender: acct.addr,
    signer: acct.signer,
    suggestedParams: sp,
    method: contract.getMethodByName("bootstrap"),
    methodArgs: [asaId],
  });
  try {
    await atc.execute(client, 4);
  } catch (e) {
    const le = wrapLogicError(e as Error)
    console.error(`${le.message}\n\n${le.stack}`);
    await performDryrun(client, atc);
    return
  }

  // Transfer some of the asset to the contract
  atc = new algosdk.AtomicTransactionComposer();
  // Create the axfer transaction to be passed into the args
  const axfer = algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
    from: acct.addr,
    to: appAddr,
    assetIndex: asaId,
    // TODO: This will cause overflow, replace with a number >= 10
    amount: 9,
    // amount: 10,
    suggestedParams: sp,
  });
  atc.addMethodCall({
    appID: appId,
    sender: acct.addr,
    signer: acct.signer,
    suggestedParams: sp,
    method: contract.getMethodByName("transfer"),
    methodArgs: [{ txn: axfer, signer: acct.signer }, asaId],
  });

  try {
    await atc.execute(client, 4);
  } catch (e) {
    const le = wrapLogicError(e as Error)
    console.error(`${le.message}\n\n${le.stack}`);
    await performDryrun(client, atc);
    return
  }

  // Call withdraw
  // TODO: fix the contract to require an asset reference passed
  atc = new algosdk.AtomicTransactionComposer();
  atc.addMethodCall({
    appID: appId,
    sender: acct.addr,
    signer: acct.signer,
    suggestedParams: sp,
    method: contract.getMethodByName("withdraw"),
    methodArgs: [asaId],
  });
  try {
    await atc.execute(client, 4);
  } catch (e) {
    const le = wrapLogicError(e as Error)
    console.error(`${le.message}\n\n${le.stack}`);
    await performDryrun(client, atc);
    return
  }
})();

async function performDryrun(
  client: algosdk.Algodv2,
  atc: algosdk.AtomicTransactionComposer
) {
  const stxnBlobs: Uint8Array[] = await atc.gatherSignatures();
  const txns: algosdk.SignedTransaction[] = stxnBlobs.map((txnBlob) => {
    return algosdk.decodeSignedTransaction(txnBlob);
  });
  const drr = await algosdk.createDryrun({ client: client, txns: txns });
  const drResult = new algosdk.DryrunResult(await client.dryrun(drr).do());
  for (const txn of drResult.txns) {
    if (txn.appCallRejected()) {
      console.log(txn.appTrace());
    }
  }
}
