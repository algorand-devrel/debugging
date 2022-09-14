package main

import (
	"context"
	"log"
	"strings"

	"github.com/algorand/go-algorand-sdk/abi"
	"github.com/algorand/go-algorand-sdk/client/v2/algod"
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
	approvalProgram, approvalBin, approvalMap := getApprovalProgram(client)
	_, clearBin, _ := getClearProgram(client)

	// Get the contract
	contract := getContract()

	log.Printf("%+v %+v %+v", approvalProgram, approvalBin, approvalMap)
	log.Printf("%+v", clearBin)

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
		log.Fatalf("Failed to get method bootstrap: %+v", err)
	}
	atc.AddMethodCall(makeParams(mcp, meth, []interface{}{axfer, asaId}))
	result, err = atc.Execute(client, context.Background(), 4)
	if err != nil {
		log.Fatalf("Failed to execute bootstrap: %+v", err)
	}
	log.Printf("Transferred: %+v", result.ConfirmedRound)

	// Bootstrap
	atc = future.AtomicTransactionComposer{}
	meth, err = contract.GetMethodByName("withdraw")
	if err != nil {
		log.Fatalf("Failed to get method bootstrap: %+v", err)
	}
	atc.AddMethodCall(makeParams(mcp, meth, []interface{}{asaId}))
	result, err = atc.Execute(client, context.Background(), 4)
	if err != nil {
		log.Fatalf("Failed to execute bootstrap: %+v", err)
	}
	log.Printf("Withdrew: %+v", result.ConfirmedRound)

}

func performDryrun() {

	// drr, err := future.CreateDryrun(client, []types.SignedTxn{s_pay, s_app, s_logic}, nil, context.Background())
	// if err != nil {
	// 	log.Fatalf("Failed to create dryrun: %+v", err)
	// }

	// filename := "go-drr.msgp"
	// os.WriteFile(filename, msgpack.Encode(drr), 0666)
	// log.Printf("Wrote to file: %s", filename)
}

func makeParams(mcp future.AddMethodCallParams, m abi.Method, a []interface{}) future.AddMethodCallParams {
	mcp.Method = m
	mcp.MethodArgs = a
	return mcp
}
