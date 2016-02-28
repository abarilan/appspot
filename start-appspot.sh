#!/bin/bash
action=$(basename $0)
action=${action%-appspot.sh}
echo AppSpot: $action
script=/var/appstore/appstore.py
if [ "$action" == "start" ]; then

echo START
nohup nice python $script > ~/appspot.log 2>&1 &

elif [ "$action" == "stop" ]; then

echo STOP

PID=$(ps -ef | grep $script | grep -v grep | awk '{ print $2 }')
if [ -z "$PID" ]; then
    echo AppSpot not running!
else
    kill $PID
fi

fi
