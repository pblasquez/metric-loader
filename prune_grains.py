#!/usr/bin/python -u

import os
import sys
from cassandra.cluster import Cluster
from cassandra import ConsistencyLevel
from cassandra.policies import ConstantReconnectionPolicy,DCAwareRoundRobinPolicy,RetryPolicy
from cassandra.query import SimpleStatement
import datetime
import time
import re
from optparse import OptionParser
from metric_groups import groups


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
    from_date = datetime.datetime.fromtimestamp(from_time)
    to_date = datetime.datetime.fromtimestamp(to_time)
    step = datetime.timedelta(days=1)
    while from_date <= to_date:
        dates = dates + ',' + str(from_date.strftime('%Y%m%d'))
        from_date += step
    dates=re.sub(r"^,", "", dates)
    dates=re.sub(r",$", "", dates)
    return dates

def main(argv):
    keyspace = 'metrics'
    session = _connect_to_cassandra(keyspace)
    usage="usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option('-f', '--from', type='int', dest='roll_from', default=int(time.time()-2592000),
        help='"from" epoch time, defaults to 0')
    parser.add_option('-t', '--to', type='int', dest='roll_to', default=int(time.time()-86401),
        help='"to" epoch time, defaults to current time')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False,
        help='View debugging information')
    parser.add_option('-x', '--test', action='store_true', dest='test', default=False,
        help='Do not execute CQL command, just print')
    (options, args) = parser.parse_args()
    from_time = int(options.roll_from)
    to_time = int(options.roll_to)
    dates = days_to_str(from_time,to_time)
    for g in groups:
        query = "DELETE FROM "+str(g)+" WHERE date in ("+str(dates)+")"
        if options.test==False:
	    result = session.execute(query)
	    if options.verbose==True:
	        print str(query)
        else:
            print str(query)

if __name__ == '__main__':
    main(sys.argv[1:])

