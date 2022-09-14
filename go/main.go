package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/algorand/go-algorand-sdk/abi"
	"github.com/algorand/go-algorand-sdk/client/v2/algod"
	"github.com/algorand/go-algorand-sdk/encoding/msgpack"
	"github.com/algorand/go-algorand-sdk/future"
	"github.com/algorand/go-algorand-sdk/types"
)

func main() {
	client, err := algod.MakeClient("http://127.0.0.1:4001", strings.Repeat("a", 64))
	if err != nil {
		log.Fatalf("Failed to init client: %+v", err)
	}

	accts, err := getSandboxAccounts()
	if err != nil {
		log.Fatalf("Failed to get accounts: %+v", err)
	}
	acct := accts[0]
	signer := future.BasicAccountTransactionSigner{Account: acct}

	// Get approval/clear programs compiled
	_, approvalBin, _ := getApprovalProgram(client)
	_, clearBin, _ := getClearProgram(client)

	// Get the contract
	contract := getContract()

	appAddr, appId := createApp(
		client,
		acct.Address,
		acct.PrivateKey,
		approvalBin,
		clearBin,
	)
	log.Printf("Created app with id: %d and address: %+v", appId, appAddr)

	asaId := createAsa(client, acct.Address, acct.PrivateKey)
	log.Printf("Created asset with id: %d", asaId)

	sp, err := client.SuggestedParams().Do(context.Background())
	if err != nil {
		log.Fatalf("Failed to get suggested params: %+v", err)
	}
	sp.FlatFee = true
	sp.Fee = 2000

	// Common parameters
	mcp := future.AddMethodCallParams{
		AppID:           appId,
		Sender:          acct.Address,
		SuggestedParams: sp,
		OnComplete:      types.NoOpOC,
		Signer:          signer,
	}

	// Bootstrap
	var atc = future.AtomicTransactionComposer{}
	meth, err := contract.GetMethodByName("bootstrap")
	if err != nil {
		log.Fatalf("Failed to get method bootstrap: %+v", err)
	}
	atc.AddMethodCall(makeParams(mcp, meth, []interface{}{asaId}))
	result, err := atc.Execute(client, context.Background(), 4)
	if err != nil {
		performDryrun(client, "bootstrap", atc)
		log.Fatalf("Failed to execute bootstrap: %+v", err)
	}
	log.Printf("Bootstrapped: %+v", result.ConfirmedRound)

	// Transfer
	atc = future.AtomicTransactionComposer{}

	// Create axfer transaction with signer
	txn, _ := future.MakeAssetTransferTxn(acct.Address.String(), appAddr.String(), 10, nil, sp, "", asaId)
	axfer := future.TransactionWithSigner{
		Txn:    txn,
		Signer: signer,
	}

	meth, err = contract.GetMethodByName("transfer")
	if err != nil {
		log.Fatalf("Failed to get method: %+v", err)
	}
	atc.AddMethodCall(makeParams(mcp, meth, []interface{}{axfer, asaId}))
	result, err = atc.Execute(client, context.Background(), 4)
	if err != nil {
		performDryrun(client, "transfer", atc)
		log.Fatalf("Failed to execute transfer: %+v", err)
	}
	log.Printf("Transferred: %+v", result.ConfirmedRound)

	// Bootstrap
	atc = future.AtomicTransactionComposer{}
	meth, err = contract.GetMethodByName("withdraw")
	if err != nil {
		log.Fatalf("Failed to get method: %+v", err)
	}
	atc.AddMethodCall(makeParams(mcp, meth, []interface{}{asaId}))
	result, err = atc.Execute(client, context.Background(), 4)
	if err != nil {
		performDryrun(client, "withdraw", atc)
		log.Fatalf("Failed to execute withdraw: %+v", err)
	}
	log.Printf("Withdrew: %+v", result.ConfirmedRound)

}

func performDryrun(client *algod.Client, name string, atc future.AtomicTransactionComposer) {
	stxnBlobs, err := atc.GatherSignatures()
	if err != nil {
		log.Fatalf("Failed to get txns from atc: %+v", err)
	}

	stxns := []types.SignedTxn{}
	for _, txn := range stxnBlobs {
		stxn := types.SignedTxn{}
		msgpack.Decode(txn, &stxn)
		stxns = append(stxns, stxn)
	}

	drr, err := future.CreateDryrun(client, stxns, nil, context.Background())
	if err != nil {
		log.Fatalf("Failed to create dryrun: %+v", err)
	}

	filename := fmt.Sprintf("%s.dr.msgp", name)
	os.WriteFile(filename, msgpack.Encode(drr), 0666)

	res, err := client.TealDryrun(drr).Do(context.Background())
	if err != nil {
		log.Fatalf("Failed to create dryrun: %+v", err)
	}

	drresp, err := future.NewDryrunResponse(res)
	if err != nil {
		log.Fatalf("Failed to parse dryrun respose: %+v", err)
	}

	for idx, txResult := range drresp.Txns {
		if txResult.AppCallRejected() {
			fmt.Printf("Failed app call in %d:\n%s", idx, txResult.GetAppCallTrace(future.DefaultStackPrinterConfig()))
		}
	}
}

func makeParams(mcp future.AddMethodCallParams, m abi.Method, a []interface{}) future.AddMethodCallParams {
	mcp.Method = m
	mcp.MethodArgs = a
	return mcp
}
