import json
import datetime
import os
import re
import time
from cassandra.cluster import Cluster
from flask import Flask, request

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
    
    return session

"""
Create the Flask application, connect to Cassandra, and then
set up all the routes. 
"""
app = Flask(__name__)
session = _connect_to_cassandra('metrics')

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

    host = str(request.args['host'])
    days = float(request.args['days'])

    to_time = int(time.time())
    to_day = int(time.strftime('%Y%m%d', time.gmtime(float(to_time))))
    from_time = to_time-int(days*24*60*60)
    from_day = int(time.strftime('%Y%m%d', time.gmtime(float(from_time))))
    day_in=''
    for x in range(from_day, to_day+1):
        day_in = day_in + ',' + str(x)
    day_in=re.sub(r"^,", "", day_in)
    day_in=re.sub(r",$", "", day_in)
    query = "SELECT * FROM metrics WHERE host='" + str(host) + "' and date IN ("
    query = query + str(day_in) + ") and time>=" + str(int(int(from_time)*1000)) + " and time<="
    query = query + str(int(int(to_time)*1000)) + " ALLOW FILTERING"
    rows = session.execute(query);

    reply={'x': []} # main json blob that will be published

    last_value={} # used to calculate the difference between counter values
    last_time={} # used to calculate the time difference between counter values

    m_row=1  #
    m_col={} # used to track index of column array position for each metric

    for r in rows:
        if str(r.metric) not in last_value:
	  last_value[r.metric]=int(r.value)
	  last_time[r.metric]=r.time
          continue # can't use the first value when dealing with counters
        # main body of work
	if str(r.time) not in reply['x']:
	  reply['x'].append(str(r.time))
        real_time = diffdates(last_time[r.metric],r.time)
        real_value = (r.value-last_value[r.metric])/int(real_time)
        last_value[r.metric]=int(r.value)
	last_time[r.metric]=r.time
        if str(r.metric) not in reply:
          reply[r.metric]=[int(real_value),]
        else:
          reply[r.metric].append(int(real_value))
    # done, return the blob
    return json.dumps(reply)

def diffdates(d1, d2):
    # 2.6 method, updated to total_seconds() in 2.7
    # the later time should be passed as the 2nd arg
    return (time.mktime(d2.timetuple()) -
               time.mktime(d1.timetuple()))

if __name__ == '__main__':
    #app.run(host='0.0.0.0')
    app.run(host='0.0.0.0',debug=True)
    #app.run(debug=True)
   # app.run()
