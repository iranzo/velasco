#!/bin/bash
[ -f .token] && . .token || echo "Configure token in .token as 'export TOKEN=...'" && exit 1
[ -f .uid ] && . .uid || echo "Configure UID in .uid as 'export UID=...'" && exit 1
python velasco.py  ${TOKEN} ${UID} | tee -a velasco.log
