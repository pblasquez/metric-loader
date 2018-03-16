import datetime
import json
import logging
import random
import requests
import sys
import time_uuid
import uuid

REST_SERVER = 'http://127.0.0.1:5000'
NUM_FACTORIES=2
NUM_SENSORS=3
NUM_READINGS=6

def _generate_random(node, num_readings, distribution="uniform", days=0):
    """
    Generate some random node data, encode that data as a JSON string, and
    transmit the request to the REST server.
    """

    for k in range(num_readings):
        if distribution == "normal":
            value = random.gauss(0, 1)
        elif distribution == "extreme":
            value = random.gauss(0, 0.2)

        # Create a timestamp sometime in the past.
        day = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        ts = time_uuid.TimeUUID.with_utc(day, randomize=False, lowest_val=True)

        # Encode our JSON values. 
        values = {'value': json.dumps( { 'node':str(node),
                                         'time': str(ts),
                                         'value': value} ) }

        # Post the data to the webserver. 
        requests.post(REST_SERVER + '/api/nodes', data=values)

def post_data():
    """
    Generate some fake data and post it to the REST server. 
    For fun, we generate three sets of data, each set representing
    a single day. Also for fun, one of those days produces more extreme data. 
    """

    for i in range(NUM_FACTORIES):
        for j in range(NUM_SENSORS):
            node = "FA-%d-node-%d" % (i, j)
            _generate_random(node, NUM_READINGS, "normal",  days=2)
            _generate_random(node, NUM_READINGS, "extreme", days=1)
            _generate_random(node, NUM_READINGS, "normal",  days=0)

def fetch_data(node, days):
    """
    Fetch data from the REST server. 
    The user can specify a specific node and
    how many days in the past to look. 
    """
    values = { 'node' : node, 
               'days'   : days }
    res = requests.get(REST_SERVER + '/api/nodes', params=values)
    return json.loads(res.text)

def main(argv=None):
    if argv[1] == 'post':
        post_data()
    elif argv[1] == 'fetch':
        if len(argv) == 4:
            node = argv[2]
            days = int(argv[3])
        else:
            node = 'FA-0-node-0'
            days = 1

        data = fetch_data(node, days)
        print json.dumps(data,
                         sort_keys=True,
                         indent=2,
                         separators=(',',':'))

if __name__ == '__main__':
    # So that we don't get so many random warnings. 
    requests_log = logging.getLogger("requests")
    requests_log.setLevel(logging.WARNING)

    main(sys.argv)
