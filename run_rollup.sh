#!/bin/sh

GRAIN=$1
EPOCH=`/bin/date +%s`
FROM=$((EPOCH-GRAIN))

/opt/metric-loader/do_rollups.py -g $GRAIN -f $FROM 2>&1 >> /var/log/rollup.log
