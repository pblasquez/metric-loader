#!/bin/sh

DIR=/opt/metric-loader
PWD=`pwd`
LOG=/var/log/metric-loader
mkdir $LOG
mkdir $DIR
mkdir $DIR/outs
mkdir $DIR/done
cp $PWD/agents.wlk $DIR/
ln -s $PWD/metric-loader.py $DIR/metric-loader.py
ln -s $PWD/metric_loader.yaml $DIR/metric_loader.yaml
ln -s $PWD/metric_groups.py $DIR/metric_groups.py
ln -s $PWD/do_rollups.py $DIR/do_rollups.py
ln -s $PWD/prune_done.py $DIR/prune_done.py
ln -s $PWD/run_multiwalk.sh $DIR/run_multiwalk.sh
ln -s $PWD/run_rollup.sh $DIR/run_rollup.sh
