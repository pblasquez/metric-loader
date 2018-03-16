import json
import datetime
import os
import re
import time
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from flask import Flask, request, make_response
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
    import StringIO
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
    #print volume
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
    #print query
    rows = session.execute(query);
    #print 'got row handle: '+str(datetime.datetime.now())
    reply={ 'x': [], # main json blob that will be published
            'metrics': {}
    }
    complete={}
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
            # divide counter delta by time delta
            real_value = 8*(this_value-last_value[r.metric])/int(real_time)
            last_value[r.metric]=int(this_value)
            last_time[r.metric]=r.time
        elif r.type=='gauge':
            real_value = this_value
        if group=='Octets':
            #multiply by 8 for Octets
            real_value=real_value*8

        if str(r.metric) not in complete:
            complete[r.metric]=[int(this_time),]
        else:
            complete[r.metric].append(int(this_time))

        if str(r.metric) not in reply['metrics']:
            reply['metrics'][r.metric]=[{'x': int(this_time), 'y': int(real_value),}]
        else:
            reply['metrics'][r.metric].append({'x': int(this_time), 'y': int(real_value)})

    # compare normal values to make sure all metrics have the same # of values
#    missing = []
#    x_indices=[]
#    for m in complete:
#        if len(reply['x']) > len(complete[m]):
#            print "Record missing for metric "+m
#            for i,n in reply['x']:
#                if n not in complete[m]:
#                    print "    missing timestamp "+n
#                    missing.append(n)
#		    x_indices.append(i)
#
#    if len(missing) > 0:
#        print "Found missing records, fixing"
#        for i in x_indices:
#            print "Deleting timestamp " + reply['x'][i]
#            del reply['x'][i]
#        for m in reply['metrics']:
#            m_indices=[]
#            for i,v in reply['metrics'][m]:
#                if reply['metrics'][m][v]['x'] in missing:
#                    m_indices.append(i)
#            for i in m_indices:
#                del reply['metrics'][m][i]
		#print "    Deleting for metric " + m
    # done, return the blob
    #print 'processed ' + str(count) + ' rows: '+str(datetime.datetime.now())
    #print json.dumps(reply)
    #return json.dumps(reply)
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.dates import DateFormatter
    from matplotlib.ticker import FuncFormatter
    import matplotlib.cm as cm
    fig=Figure()
    ax=fig.add_subplot(111)
    ax.grid()
    ax.spines["top"].set_visible(False)  
    ax.spines["bottom"].set_visible(False)  
    ax.spines["right"].set_visible(False)  
    ax.spines["left"].set_visible(False)  
    length = len(reply['metrics'])
    for m in reply['metrics']:
        x=[]
        y=[]
	mod=1
        color='blue'
        line='b-'
	polarityCompile = re.compile( r'^.*Out.*')
	if polarityCompile.search(m):
	    mod=-1
            color='green'
            line='g-'
        for v in reply['metrics'][m]:
            x.append(datetime.datetime.fromtimestamp(v['x']))
            y.append(v['y']*mod)
        ax.plot_date(x, y, line)
        ax.xaxis.set_major_formatter(DateFormatter('%m/%d/%Y %H:%M'))
        #ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        ax.yaxis.set_major_formatter(FuncFormatter(get_suffix))
        ax.fill_between(x, 0, y, color=color)
        for tick in ax.xaxis.get_major_ticks():
	    tick.label.set_fontsize(8)
	    tick.label.set_rotation('vertical')
    fig.autofmt_xdate(rotation=40)
    canvas=FigureCanvas(fig)
    png_output = StringIO.StringIO()
    canvas.print_png(png_output)
    response=make_response(png_output.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response

def get_suffix(i,pos):
    suffix = 'b'
    div = 1
    s_map = { 1000: 'k', 1000000: 'm', 1000000000: 'g' }
    for d in s_map:
        if i > 0:
            if i > d:
                suffix = s_map[d]
                div = d
        else:
            e=d*-1
            if i < e:
                suffix = s_map[d]
                div = d
    return str(i/div)+suffix+'/s'

def diffdates(d1, d2):
    # 2.6 method, updated to total_seconds() in 2.7
    # the later time should be passed as the 2nd arg
    return (time.mktime(d2.timetuple()) -
               time.mktime(d1.timetuple()))

if __name__ == '__main__':
    #app.run(host='0.0.0.0')
    app.run(host='0.0.0.0',port=5002,debug=True)
    #app.run(debug=True)
   # app.run()
