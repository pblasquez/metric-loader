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

    cluster = Cluster([host])
    session = cluster.connect(keyspace)
    
    return session

"""
Create the Flask application, connect to Cassandra, and then
set up all the routes. 
"""
app = Flask(__name__)
session = _connect_to_cassandra('metrics')

@app.route('/api/metrics', methods=['GET'])
def get_nodes():
    """
    Fetch the node data from the Cassandra cluster. 
    The user can filter by node, and the number
    of days in the past. 
    """

    host = str(request.args['host'])
    metric = str(request.args['metric'])
    days = int(request.args['days'])

    to_time = int(time.time())
    to_day = int(time.strftime('%Y%m%d', time.gmtime(float(to_time))))
    from_time = to_time-int(days*24*60*60)
    from_day = int(time.strftime('%Y%m%d', time.gmtime(float(from_time))))
    day_in=''
    for x in range(from_day, to_day+1):
        day_in = day_in + ',' + str(x)
    day_in=re.sub(r"^,", "", day_in)
    day_in=re.sub(r",$", "", day_in)
    query = "SELECT * FROM metrics WHERE metric='" + str(metric) + "' and date IN ("
    query = query + str(day_in) + ") and time>=" + str(int(int(from_time)*1000)) + " and time<="
    query = query + str(int(int(to_time)*1000))
    rows = session.execute(query);
    reply={}
    for index, r in enumerate(rows):
        if str(r.metric) not in reply:
          reply[r.metric]=[]
        if index==0:
          continue
        real_value = (r.value-rows[index-1].value)/300
        reply[str(r.metric)].append({ 'value': int(real_value),
                               'time': str(r.time) })
    return json.dumps(reply)

if __name__ == '__main__':
    app.run(debug=True)
   # app.run()
