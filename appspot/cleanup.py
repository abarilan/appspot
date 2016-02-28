#!/usr/bin/env python


import os, sys, time

root = sys.argv[1]
target = sys.argv[2]

DAYS = 60
purge_time = time.time() - DAYS*24*60*60

for path, dirs, files in os.walk(root, False):

    if dirs:
        continue
    if os.path.isfile(os.path.join(path, "KEEP")):
        continue
    ctime = os.path.getctime(path)
    if ctime >= purge_time:
        continue

    print "removing", path, "ctime:", time.ctime(ctime)
    
    os.rename(path, os.path.join(target, path.replace("/","-")))
    
#    for f in files:
#        os.remove(os.path.join(path, f))
#    os.rmdir(path)
    
# second pass -- delete empty dirs
while True:
    deleted = 0
    for path, dirs, files in os.walk(root, False):
        if not dirs and not files:
            print "removing empty directory", path
            os.rmdir(path)
            deleted += 1
    if not deleted:
        break
