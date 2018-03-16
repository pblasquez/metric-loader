#!/usr/bin/python -u

import os
import shutil
import errno
import time
import multiprocessing
from cassandra.cluster import Cluster
import yaml
import re
from metric_groups import groups, metric_map



def _connect_to_cassandra(keyspace):
    """
    Connect to the Cassandra cluster and return the session.
    """

    if 'BACKEND_STORAGE_IP' in os.environ:
        host = os.environ['BACKEND_STORAGE_IP']
    else:
        host = '127.0.0.1'

    cluster = Cluster([host,'127.0.0.1'])
    session = cluster.connect(keyspace)
    session.default_timeout=60
    return session

def clean_mib_markup(v):
    markup = {
        '^Counter32:\s+': int,
        '^Counter64:\s+': int,
        '^STRING:\s+': str,
        '^OID:\s+': str
    }
    for k in markup:
        m = re.compile(k)
	if m.match(v):
            v = re.sub(k,'', v)
	    markup[k](v)
            return v
    return v

def loader(file,dest,ts):
    this_config={}
    node={}
    config_file = '/opt/metric-loader/metric_loader.yaml'
    with open(config_file) as f:
        config = yaml.load(f)
    host = re.sub(r'^.*\/(.*?)\.(?:mwalk|part).*$', r"\1", file)
    if host not in node:
	node[host] = {}
	node[host]['system'] = {}
	node[host]['interface'] = {}
    if host in config['hosts']:
        for c in config['hosts'][host]['collections']:
            this_config.update(config['collections'][c])
    else:
        for c in config['hosts']['default']['collections']:
            this_config.update(config['collections'][c])
    with open(file,'r') as fh:
        for line in fh.readlines():
            matchObj = re.match(r'^(\d+)\s+(.*?)::(.*) = (.*)', line)
            if matchObj:
                value = matchObj.group(4).replace('"','')
                for k in this_config['system']:
                    if this_config['system'][k]==matchObj.group(3):
                        if k not in node[host]['system']:
                            node[host]['system'][k] = clean_mib_markup(value)
                for i in this_config['interface']:
                    regex = re.compile(r'^(%s)\.(\d+).*'%this_config['interface'][i])
                    intMatch = regex.match(matchObj.group(3))
                    if intMatch:
                        ifIndex = intMatch.group(2)
			if ifIndex not in node[host]['interface']:
                            node[host]['interface'][ifIndex]={}
			node[host]['interface'][ifIndex][i] = clean_mib_markup(value)
    shutil.move(file,dest)
    session = _connect_to_cassandra('metrics')
    for i in node[host]['interface']:
        for k in node[host]['interface'][i]:
            if k != 'description':
                metric = node[host]['interface'][i]['description']+'::'+k
                group = metric_map[k]
                query = "INSERT INTO "+str(group)+"""(host, metric, time, date, type, value)
                           VALUES (%(node)s, %(metric)s, %(time)s, %(date)s, %(type)s, %(value)s)
                           USING TTL 604800
                           """
            
                index_query = """INSERT INTO metrics_index
                           (host, group, metric)
                           VALUES (%(node)s, %(group)s, %(metric)s)
                           """
                values = { 'node': str(host),
                           'time': long(int(ts)*1000),
                           'date': int(time.strftime('%Y%m%d', time.gmtime(float(ts)))),
                           'group': str(group),
                           'metric': str(metric),
                           'type': str('counter'),
                           'value': float(node[host]['interface'][i][k]) }

                index_values = { 'node': str(host),
			   'group': str(group),
                           'metric': str(metric) }
                #print query%values
                session.execute(query, values)
                session.execute(index_query, index_values)
    return

if __name__ == '__main__':
    root = '/opt/metric-loader/outs' # define root directory for all files here
    done = '/opt/metric-loader/done' # define directory for finished files here
    jobs = [] # multiprocess tracker
    dirs = {} # cleanup tracking
    # directory structure is <root>/<timestamp>/<file>
    # outer loop is timestamp directories
    for d in os.listdir(root):
        # inner loop is files within those directories
        this_dir = root+'/'+d # define this directory
        done_dir = done+'/'+d # define done directory for this
        dirs[this_dir]=done_dir # add to cleanup list
        try:
            os.makedirs(done_dir) # should mkdir, exist, or raise error
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(done_dir):
                pass
            else: raise
        for f in os.listdir(this_dir): # doing files now
            this_file = this_dir+'/'+f # define absolute path of this file
            this_dest = done_dir+'/'+f # define absolute path of this file
            l = multiprocessing.Process(name=this_file, target=loader, args=(this_file,this_dest,d))
            jobs.append(l)
            l.start()
    for j in jobs: # checking jobs
        j.join # wait for job to finish
    for d in dirs: # jobs are finished, cleanup dirs
        try:
            os.rmdir(d)
        except OSError as exc:
            if exc.errno == errno.ENOTEMPTY:
                pass # no worries we'll get it next run
            else: raise
