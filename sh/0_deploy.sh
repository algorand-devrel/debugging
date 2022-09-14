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
if [ -z ${1+x} ]; then
  APP_ID=$(${GOAL} app create \
    --creator ${ACCT} \
    --approval-prog approval.teal \
    --clear-prog clear.teal \
    --global-byteslices 0 --global-ints 1 \
    --local-byteslices 0 --local-ints 0 \
    | grep 'Created app with app index' \
    | awk '{print $6}' \
    | tr -d '\r')
else
  ${GOAL} app create \
    --creator ${ACCT} \
    --approval-prog approval.teal \
    --clear-prog clear.teal \
    --global-byteslices 0 --global-ints 1 \
    --local-byteslices 0 --local-ints 0 \
    --dryrun-dump \
    --out withdraw.dr
  
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
  
  ${TDBG} debug -d withdraw.dr
fi

