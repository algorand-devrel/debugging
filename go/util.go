package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"os"

	"github.com/algorand/go-algorand-sdk/abi"
	"github.com/algorand/go-algorand-sdk/client/kmd"
	"github.com/algorand/go-algorand-sdk/client/v2/algod"
	"github.com/algorand/go-algorand-sdk/crypto"
	"github.com/algorand/go-algorand-sdk/future"
	"github.com/algorand/go-algorand-sdk/logic"
	"github.com/algorand/go-algorand-sdk/types"
)

const (
	KMD_ADDRESS         = "http://localhost:4002"
	KMD_TOKEN           = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	KMD_WALLET_NAME     = "unencrypted-default-wallet"
	KMD_WALLET_PASSWORD = ""

	ARTIFACT_DIR = "../contracts/artifacts"
)

func getSandboxAccounts() ([]crypto.Account, error) {
	client, err := kmd.MakeClient(KMD_ADDRESS, KMD_TOKEN)
	if err != nil {
		return nil, fmt.Errorf("Failed to create client: %+v", err)
	}

	resp, err := client.ListWallets()
	if err != nil {
		return nil, fmt.Errorf("Failed to list wallets: %+v", err)
	}

	var walletId string
	for _, wallet := range resp.Wallets {
		if wallet.Name == KMD_WALLET_NAME {
			walletId = wallet.ID
		}
	}

	if walletId == "" {
		return nil, fmt.Errorf("No wallet named %s", KMD_WALLET_NAME)
	}

	whResp, err := client.InitWalletHandle(walletId, KMD_WALLET_PASSWORD)
	if err != nil {
		return nil, fmt.Errorf("Failed to init wallet handle: %+v", err)
	}

	addrResp, err := client.ListKeys(whResp.WalletHandleToken)
	if err != nil {
		return nil, fmt.Errorf("Failed to list keys: %+v", err)
	}

	var accts []crypto.Account
	for _, addr := range addrResp.Addresses {
		expResp, err := client.ExportKey(whResp.WalletHandleToken, KMD_WALLET_PASSWORD, addr)
		if err != nil {
			return nil, fmt.Errorf("Failed to export key: %+v", err)
		}

		acct, err := crypto.AccountFromPrivateKey(expResp.PrivateKey)
		if err != nil {
			return nil, fmt.Errorf("Failed to create account from private key: %+v", err)
		}

		accts = append(accts, acct)
	}

	return accts, nil
}

func compile(client *algod.Client, program []byte) ([]byte, logic.SourceMap) {
	res, err := client.TealCompile(program).Sourcemap(true).Do(context.Background())
	if err != nil {
		log.Fatalf("Failed to compile program: %+v", err)
	}

	b, err := base64.StdEncoding.DecodeString(res.Result)
	if err != nil {
		log.Fatalf("Failed to decode program: %+v", err)
	}

	sm, err := logic.DecodeSourceMap(*res.Sourcemap)
	if err != nil {
		log.Fatalf("Failed to decode source map: %+v", err)
	}

	return b, sm
}

func getClearProgram(client *algod.Client) (string, []byte, logic.SourceMap) {
	b, err := os.ReadFile(ARTIFACT_DIR + "/clear.teal")
	if err != nil {
		log.Fatalf("Failed to read file: %+v", err)
	}
	bin, sm := compile(client, b)
	return string(b), bin, sm
}

func getApprovalProgram(client *algod.Client) (string, []byte, logic.SourceMap) {
	b, err := os.ReadFile(ARTIFACT_DIR + "/approval.teal")
	if err != nil {
		log.Fatalf("Failed to read file: %+v", err)
	}
	bin, sm := compile(client, b)
	return string(b), bin, sm
}

func getContract() *abi.Contract {
	b, err := ioutil.ReadFile(ARTIFACT_DIR + "/contract.json")
	if err != nil {
		log.Fatalf("Failed to open contract file: %+v", err)
	}
	contract := &abi.Contract{}
	if err := json.Unmarshal(b, contract); err != nil {
		log.Fatalf("Failed to marshal contract: %+v", err)
	}
	return contract
}

func createApp(client *algod.Client, sender types.Address, privateKey, approvalProg, clearProg []byte) (types.Address, uint64) {
	gschema := types.StateSchema{
		NumUint:      1,
		NumByteSlice: 0,
	}
	lschema := types.StateSchema{
		NumUint:      0,
		NumByteSlice: 0,
	}

	sp, err := client.SuggestedParams().Do(context.Background())
	if err != nil {
		log.Fatalf("Couldnt get suggested params: %+v", err)
	}

	txn, err := future.MakeApplicationCreateTx(false, approvalProg, clearProg, gschema, lschema, nil, nil, nil, nil, sp, sender, nil, types.Digest{}, [32]byte{}, types.Address{})
	if err != nil {
		log.Fatalf("Failed to make app create transaction: %+v", err)
	}

	txid, txBlob, err := crypto.SignTransaction(privateKey, txn)
	if err != nil {
		log.Fatalf("Couldnt sign transaction: %+v", err)
	}

	_, err = client.SendRawTransaction(txBlob).Do(context.Background())
	if err != nil {
		log.Fatalf("Failed to send transaction: %+v", err)
	}

	result, err := future.WaitForConfirmation(client, txid, 4, context.Background())
	if err != nil {
		log.Fatalf("Failed to get pending result: %+v", err)
	}
	appId := result.ApplicationIndex
	appAddr := crypto.GetApplicationAddress(result.ApplicationIndex)

	// Created app, now fund app address
	txn, err = future.MakePaymentTxn(sender.String(), appAddr.String(), uint64(1e8), nil, "", sp)
	if err != nil {
		log.Fatalf("Failed to make payment transaction: %+v", err)
	}

	txid, txBlob, err = crypto.SignTransaction(privateKey, txn)
	if err != nil {
		log.Fatalf("Couldnt sign transaction: %+v", err)
	}
	// Assume no errors
	client.SendRawTransaction(txBlob).Do(context.Background())
	future.WaitForConfirmation(client, txid, 4, context.Background())

	return appAddr, appId
}

func createAsa(client *algod.Client, sender types.Address, privateKey []byte) uint64 {
	sp, err := client.SuggestedParams().Do(context.Background())
	if err != nil {
		log.Fatalf("Couldnt get suggested params: %+v", err)
	}

	txn, err := future.MakeAssetCreateTxn(sender.String(), nil, sp, 100000, 0, false, "", "", "", "", "tmp", "tmp_asset", "", "")
	if err != nil {
		log.Fatalf("Failed to make asset create transaction: %+v", err)
	}

	txid, txBlob, err := crypto.SignTransaction(privateKey, txn)
	if err != nil {
		log.Fatalf("Couldnt sign transaction: %+v", err)
	}

	_, err = client.SendRawTransaction(txBlob).Do(context.Background())
	if err != nil {
		log.Fatalf("Failed to send transaction: %+v", err)
	}

	result, err := future.WaitForConfirmation(client, txid, 4, context.Background())
	if err != nil {
		log.Fatalf("Failed to get pending result: %+v", err)
	}
	return result.AssetIndex
}
