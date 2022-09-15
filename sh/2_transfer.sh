#!/usr/bin/env bash

set -e -u -x -o pipefail

SB=~/sandbox/sandbox
GOAL="${SB} goal"
TDBG="${SB} tealdbg"

ACCT=$(${GOAL} account list | grep '[online]' | head -n 1 | tail -n 1 | awk '{print $3}' | tr -d '\r')

APPROVAL_TEAL=../contracts/artifacts/approval.teal
CLEAR_TEAL=../contracts/artifacts/clear.teal

# Move contracts to sandbox
cp ${APPROVAL_TEAL} .
cp ${CLEAR_TEAL} .
${SB} copyTo approval.teal
${SB} copyTo clear.teal
rm approval.teal clear.teal

# Deploy Smart Contract
APP_ID=$(${GOAL} app create \
  --creator ${ACCT} \
  --approval-prog approval.teal \
  --clear-prog clear.teal \
  --global-byteslices 0 --global-ints 1 \
  --local-byteslices 0 --local-ints 0 \
  | grep 'Created app with app index' \
  | awk '{print $6}' \
  | tr -d '\r')
# Application Address
APP_ADDR=$(${GOAL} app info --app-id ${APP_ID} \
  | grep 'Application account' \
  | awk '{print $3}' \
  | tr -d '\r')

# Create Asset
ASSET_ID=$(${GOAL} asset create \
  --creator ${ACCT} \
  --name "tmp_asset" \
  --unitname "tmp" \
  --total 10000 \
  --decimals 0 \
  | grep 'Created asset with asset index' \
  | awk '{print $6}' \
  | tr -d '\r')

# Fund Application Address
${GOAL} clerk send \
  --from ${ACCT} \
  --to ${APP_ADDR} \
  --amount 200000

# Bootstrap
${GOAL} app method \
  --from ${ACCT} \
  --app-id ${APP_ID} \
  --method "bootstrap(asset)void" \
  --arg ${ASSET_ID} \
  --fee 2000

# Transfer
# TODO: Prevent underflow by increasing the value you pass
# --amount 10
if [ -z ${1+x} ]; then
  ${GOAL} asset send \
    --from ${ACCT} \
    --to ${APP_ADDR} \
    --assetid ${ASSET_ID} \
    --amount 9 \
    --out axfer.txn
  ${GOAL} app method \
    --from ${ACCT} \
    --app-id ${APP_ID} \
    --method "transfer(axfer,asset)void" \
    --arg axfer.txn \
    --arg ${ASSET_ID} \
    --fee 2000
else
  ${GOAL} asset send \
    --from ${ACCT} \
    --to ${APP_ADDR} \
    --assetid ${ASSET_ID} \
    --amount 9 \
    --out axfer.txn
  ${GOAL} app method \
    --from ${ACCT} \
    --app-id ${APP_ID} \
    --method "transfer(axfer,asset)void" \
    --arg axfer.txn \
    --arg ${ASSET_ID} \
    --fee 2000 \
    --dryrun-dump \
    --out transfer.dr
  
  set +x
  echo
  echo "###########################################################"
  echo "#                                                         #"
  echo "#                                                         #"
  echo "#   Visit: chrome://inspect in a Chromium based browser   #"
  echo "#                                                         #"
  echo "#                                                         #"
  echo "###########################################################"
  echo
  set -x
  
  ${TDBG} debug -d transfer.dr
fi

