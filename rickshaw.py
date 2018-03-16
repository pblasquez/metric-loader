import json
import datetime
import os
import re
import time
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from flask import Flask, request
from metric_groups import groups,metric_map

def _connect_to_cassandra(keyspace):
    """
    Connect to the Cassandra cluster and return the session. 
    """

    if 'BACKEND_STORAGE_IP' in os.environ:
        host = os.environ['BACKEND_STORAGE_IP']
    else:
        host = '127.0.0.1'

    cluster = Cluster([host])
    session = cluster.connect(keyspace)
    session.default_fetch_size=50000
    return session

"""
Create the Flask application, connect to Cassandra, and then
set up all the routes. 
"""
app = Flask(__name__)
session = _connect_to_cassandra('metrics')
print 'got session, preparing rows '+str(datetime.datetime.now())

@app.route('/api/index/<hosts>', methods=['GET'])
def list_nodes(hosts):
    """
    Fetch the node and metric list from the Cassandra cluster. 
    """
    if hosts=='hosts':
      query = "SELECT DISTINCT host FROM metrics_index";
      reply=[]
    elif hosts=='all':
      query = "SELECT * FROM metrics_index";
      reply={}

    rows = session.execute(query);
    for r in rows:
        if hosts=='hosts':
          if str(r.host) not in reply:
            reply.append(str(r.host))
        elif hosts=='all':
          if str(r.host) not in reply:
            reply[str(r.host)]=[]
          if str(r.metric) not in reply[str(r.host)]:
            reply[str(r.host)].append(str(r.metric))
    return json.dumps(reply)

@app.route('/api/metrics', methods=['GET'])
def get_nodes():
    """
    Fetch the node data from the Cassandra cluster. 
    The user can filter by node, and the number
    of days in the past. 
    """
    #print 'Starting at '+str(datetime.datetime.now())

    host = str(request.args['host'])
    days = float(request.args['days'])
    metric_like = str(request.args['metric_like'])  #  accept metric_like variable from GET
    group = str(request.args['group'])  #  accept metric_like variable from GET
    volume = str(request.args['volume'])  #  accept metric_like variable from GET

    to_time = int(time.time())
    to_day = int(time.strftime('%Y%m%d', time.gmtime(float(to_time))))
    from_time = to_time-int(days*24*60*60)
    from_day = int(time.strftime('%Y%m%d', time.gmtime(float(from_time))))
    day_in=''
    for x in range(from_day, to_day+1):
        day_in = day_in + ',' + str(x)
    day_in=re.sub(r"^,", "", day_in)
    day_in=re.sub(r",$", "", day_in)
    rollup=False
    rollpoint=days
    table=group
    print volume
    if volume=='overlay':
        rollpoint=rollpoint*2
    if rollpoint > 1:
        rollup=True
        if rollpoint > 7:
            if rollpoint > 30:
                table=table+'86400'
            else:
                table=table+'7200'
        else:
            table=table+'1800'
    query = "SELECT * FROM "+table+" WHERE host='" + str(host) + "' and date IN ("
    query = query + str(day_in) + ") and time>=" + str(int(int(from_time)*1000)) + " and time<="
    query = query + str(int(int(to_time)*1000)) + " ALLOW FILTERING"
    #print 'getting row handle at '+str(datetime.datetime.now())
    print query
    rows = session.execute(query);
    #print 'got row handle: '+str(datetime.datetime.now())
    reply={ 'x': [], # main json blob that will be published
            'metrics': {}
    }
    last_value={} # used to calculate the difference between counter values
    last_time={} # used to calculate the time difference between counter values
    compileObj = re.compile( r'^'+metric_like+'::(.*)')

    m_row=1  #
    m_col={} # used to track index of column array position for each metric
    # count=0
    for r in rows:
        if rollup==True:
            this_value=r.max
        else:
            this_value = r.value
        #count+=1
        #if(count%20000==0):
         #   print str(count) + ' records at ' + str(datetime.datetime.now())
        if metric_like:
          if compileObj.search(r.metric):
            #print r.metric
            if group:
              if groups[group]:
                this_group = compileObj.match(r.metric).group(1)
                if not this_group in groups[group]:
                    continue
          else:
              continue
        elif group:
          if groups[group]:
            found=False
            for g in groups[group]:
               groupCompile = re.compile( r'^.*::.*'+g)
               if groupCompile.search(r.metric):
                   found=True
            if found==False:
                continue
        this_time = int(time.mktime(r.time.timetuple()))
        if r.type=='counter':
            if str(r.metric) not in last_value:
              last_value[r.metric]=int(this_value)
              last_time[r.metric]=r.time
              continue # can't use the first value when dealing with counters
            # main body of work
            if this_time not in reply['x']:
              reply['x'].append(this_time)
            real_time = diffdates(last_time[r.metric],r.time)
            # divide counter delta by time delta and multiply by 8 for bits
            real_value = 8*(this_value-last_value[r.metric])/int(real_time)
            last_value[r.metric]=int(this_value)
            last_time[r.metric]=r.time
        elif r.type=='gauge':
            # multiply by 8 for bits
            real_value = 8*this_value

        if str(r.metric) not in reply['metrics']:
            reply['metrics'][r.metric]=[{'x': int(this_time), 'y': int(real_value),}]
        else:
            reply['metrics'][r.metric].append({'x': int(this_time), 'y': int(real_value)})
    # done, return the blob
    #print 'processed ' + str(count) + ' rows: '+str(datetime.datetime.now())
    #print json.dumps(reply)
    return json.dumps(reply)

def diffdates(d1, d2):
    # 2.6 method, updated to total_seconds() in 2.7
    # the later time should be passed as the 2nd arg
    return (time.mktime(d2.timetuple()) -
               time.mktime(d1.timetuple()))

if __name__ == '__main__':
    #app.run(host='0.0.0.0')
    app.run(host='0.0.0.0',port=5001,debug=True)
    #app.run(debug=True)
   # app.run()
