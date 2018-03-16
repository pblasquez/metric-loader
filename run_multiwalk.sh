#!/bin/sh

ROOT_DIR="/opt/metric-loader"
EPOCH=`/bin/date +%s`
EPOCH_DIR="$ROOT_DIR/outs/$EPOCH"
DONE_DIR="$ROOT_DIR/done/$EPOCH"
AGENT_FILE="$ROOT_DIR/agents.wlk"

mkdir $EPOCH_DIR
/usr/local/bin/multiwalk2c -f $AGENT_FILE -T 60 -t 5 -r 5 -m 1 -o $EPOCH_DIR -e 1 -n 0 -L sysName,sysObjectID,ifTable,ifXTable 2>&1 >> /var/log/metric-loader/multiwalk.log
$ROOT_DIR/metric-loader.py 2>&1 >> /var/log/metric-loader/loader.log
/bin/gzip $DONE_DIR/*
