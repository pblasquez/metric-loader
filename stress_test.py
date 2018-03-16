import cProfile
import json
import datetime
import os
import re
import time
from cassandra.cluster import Cluster

def _connect_to_cassandra(keyspace):
    """
    Connect to the Cassandra cluster and return the session. 
    """

    if 'BACKEND_STORAGE_IP' in os.environ:
        host = os.environ['BACKEND_STORAGE_IP']
    else:
        host = '127.0.0.1'

    cluster = Cluster([host,])
    session = cluster.connect(keyspace)
    session.default_fetch_size=200000
    session.default_timeout=60
    
    return session

"""
Create the Flask application, connect to Cassandra, and then
set up all the routes. 
"""
session = _connect_to_cassandra('metrics')

host = str('host.domain.name')
days = float(.1)

to_time = int(time.time())
to_day = int(time.strftime('%Y%m%d', time.gmtime(float(to_time))))
from_time = to_time-int(days*24*60*60)
from_day = int(time.strftime('%Y%m%d', time.gmtime(float(from_time))))
day_in=''

for x in range(from_day, to_day+1):
  day_in = day_in + ',' + str(x)

day_in=re.sub(r"^,", "", day_in)
day_in=re.sub(r",$", "", day_in)
query = "SELECT * FROM Octets WHERE host='" + str(host) + "' and date IN ("
query = query + str(day_in) + ") and time>=" + str(int(int(from_time)*1000)) + " and time<="
query = query + str(int(int(to_time)*1000)) + " ALLOW FILTERING"
print 'getting rows: '+str(datetime.datetime.now())
rows = session.execute(query)
print 'got row handle: '+str(datetime.datetime.now())
reply={}
last_value={}
count=int(0);
for r in rows:
    count+=1
    if(count%20000==0):
      print str(count) + ' records at ' + str(datetime.datetime.now())
    if str(r.host) not in reply:
      reply[r.host]={}
      last_value[r.host]={}
    if str(r.metric) not in reply[r.host]:
      reply[r.host][r.metric]=[]
      last_value[r.host][r.metric]=int(r.value)
      continue
    real_value = (r.value-last_value[r.host][r.metric])/60
    last_value[r.host][r.metric]=int(r.value)
    reply[str(r.host)][r.metric].append({
      'value': int(real_value),
      'time': str(r.time)
    })
print 'processed ' + str(count) + ' rows: '+str(datetime.datetime.now())
