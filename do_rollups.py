#!/usr/bin/python -u

import os
import sys
from optparse import OptionParser
import time
import multiprocessing
from cassandra.cluster import Cluster
from cassandra import ConsistencyLevel
from cassandra.policies import ConstantReconnectionPolicy,DCAwareRoundRobinPolicy,RetryPolicy
from cassandra.query import SimpleStatement
import yaml
import re
import json
from metric_groups import groups, metric_map


def _connect_to_cassandra(keyspace):
    """
    Connect to the Cassandra cluster and return the session.
    """

    if 'BACKEND_STORAGE_IP' in os.environ:
        host = os.environ['BACKEND_STORAGE_IP']
    else:
        host = '127.0.0.1'
    retry=RetryPolicy()
    retry.RETRY=10
    cluster = Cluster(
        [host,'127.0.0.1',],
        reconnection_policy=ConstantReconnectionPolicy(5.0, 100),
        load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="ASH2"),
        default_retry_policy=retry
    )
    session = cluster.connect(keyspace)
    session.default_timeout = 9999
    session.default_fetch_size = 1000

    return session

def days_to_str(from_time,to_time):
    dates=''
    from_day = int(time.strftime('%Y%m%d', time.gmtime(float(from_time))))
    to_day = int(time.strftime('%Y%m%d', time.gmtime(float(to_time))))
    for x in range(from_day, to_day+1):
        dates = dates + ',' + str(x)
    dates=re.sub(r"^,", "", dates)
    dates=re.sub(r",$", "", dates)
    return dates

def diffdates(d1, d2):
    # 2.6 method, updated to total_seconds() in 2.7
    # the later time should be passed as the 2nd arg
    return (time.mktime(d2.timetuple()) -
               time.mktime(d1.timetuple()))

def loader(grain,ts_list,table):
    keyspace = 'metrics'
    session = _connect_to_cassandra(keyspace)
    metrics={}
    dates=[]
    # begin GET
    #print str(grain)+','+str(ts_list)+','+table
    index_q = "SELECT * FROM metrics_index"
    index_r = session.execute(index_q)
    for r in index_r:
        if r.host not in metrics:
            metrics[str(r.host)] = {}
            
    for g in groups:
        #print 'doing table '+g
        for ts in ts_list:
            from_time = int(ts)
            to_time = int(int(ts)+int(grain))
            dates = days_to_str(from_time,to_time)
            for h in metrics:
                query = "SELECT * from "+str(g)+" WHERE host = '"+str(h)+"' AND date in ("+str(dates)+") "
                query = query + "AND time >= "+str(int(from_time*1000))+" AND time <= "+str(int(to_time*1000))+" ALLOW FILTERING"
                #print query
                rows = session.execute(query)
                last_value={} # used to calculate the difference between counter values
                last_time={} # used to calculate the time difference between counter values
                for r in rows:
                    if str(r.type)=='counter':
                        #print 'calculating '+h+'-'+r.metric
                        if r.metric not in last_value:
                            last_value[r.metric]=int(r.value)
                            last_time[r.metric]=r.time
                            continue # can't use the first value when dealing with counters
                        real_time = diffdates(last_time[r.metric],r.time)
                        real_value = (r.value-last_value[r.metric])/int(real_time)
                        last_value[r.metric]=int(r.value)
                        last_time[r.metric]=r.time
                    else:
                        real_value = r.value
                    #print 'doing '+h+'::'+r.metric
                    if str(r.metric) not in metrics[h]:
                        metrics[h][r.metric] = {}
                        metrics[h][r.metric][r.date]=[int(real_value),]
                        #print 'initiating date:'+str(r.date)+' for metric '+r.metric
                    else:
                        metrics[h][r.metric][r.date].append(int(real_value))
                    #print 'appending value:'+str(real_value)+' for metric '+h+'-'+r.metric

    # end GET
    # begin INSERT
    for h in metrics:
        for m in metrics[h]:
            g = metric_map[str(m.split('::')[1])]
            r_table=g+str(grain)
            this_index = "INSERT INTO %s_index (host,group,metric) VALUES ('%s','%s','%s')" % (table,h,g,m)
	    #print this_index
            ss_index = SimpleStatement(this_index, consistency_level=ConsistencyLevel.ANY)
	    session.execute(ss_index)
            #print 'doing metric '+m
            for d in metrics[h][m]:
                this_min = min(metrics[h][m][d])
                this_max = max(metrics[h][m][d])
                this_avg = sum(metrics[h][m][d])/len(metrics[h][m][d])
                this_query = "INSERT INTO %s (date,host,time,metric,avg,min,max,type) VALUES (%d,'%s',%d,'%s',%d,%d,%d,'%s')"
                bound = this_query % (r_table,d,h,int(ts_list[0]*1000),m,this_avg,this_min,this_max,'gauge')
                #print bound
                ss_query = SimpleStatement(bound, consistency_level=ConsistencyLevel.ONE)
		session.execute(ss_query)
    return

def main(argv):
    rollup_table = { # define grain to cassandra table mappings
        1800:  'rollups1800',
        7200:  'rollups7200',
        86400: 'rollups86400'
    }
    rollups = {}
    usage="usage: %prog [options]"
    choices = ['1800','7200','86400']
    use_table={}
    parser = OptionParser(usage)
    parser.add_option('-f', '--from', type='int', dest='roll_from', default=int(time.time()-86400),
        help='"from" epoch time, defaults to 0')
    parser.add_option('-t', '--to', type='int', dest='roll_to', default=int(time.time()),
        help='"to" epoch time, defaults to current time')
    parser.add_option('-g', '--grain', dest='grain', choices=choices,
        help='Specify which grains to rollup')
    (options, args) = parser.parse_args()
    if options.grain in choices:
        this_grain = int(options.grain)
        use_table[this_grain] = rollup_table[this_grain]
    else:
        use_table = rollup_table
    roll_diff = options.roll_to - options.roll_from
    for grain in use_table:
        this_grain = int(str(grain))
        if roll_diff >= this_grain:
            start_point = options.roll_from-(options.roll_from%this_grain)
            rollups[this_grain] = [start_point,]
            intervals = roll_diff/this_grain
            for x in range(1, intervals):
                rollups[this_grain].append(start_point+(x*this_grain))
    
    jobs = [] # multiprocess tracker
    for this_grain in rollups:
        for this_ts in rollups[this_grain]:
            ts_list = (this_ts,)
	    this_name = str(this_grain)+'-'+str(this_ts)
            #print 'starting '+this_name
            l = multiprocessing.Process(name=this_name, target=loader, args=(this_grain,ts_list,rollup_table[this_grain]))
            jobs.append(l)
            l.start()
    for j in jobs: # checking jobs
        j.join # wait for job to finish

if __name__ == '__main__':
    main(sys.argv[1:])

