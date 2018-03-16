#!/usr/bin/python

import os
import shutil
import time

retain = 3 # amount of data to retain, as amount of days
done_dir = '/opt/metric-loader/done' # directory to work on
epoch = int(time.time())
limit = int(epoch-(retain*24*60*60))
for d in os.listdir(done_dir):
  this_epoch = int(d)
  if this_epoch<limit:
    this_dir = done_dir+'/'+d
    shutil.rmtree(this_dir)
    print 'Removed ' + this_dir
