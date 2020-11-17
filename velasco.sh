#!/bin/bash
[ -f .token ] && export TOKEN=$(cat .token | xargs echo) || echo "Configure token in .token as 'export TOKEN=...'" || exit 1
[ -f .uid ] && export USERID=$(cat .uid | xargs echo) || echo "Configure UID in .uid as 'export UID=...'" || exit 1
python velasco.py ${TOKEN} ${USERID} | tee -a velasco.log
