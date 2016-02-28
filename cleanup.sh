#!/bin/bash -ex

cd $(dirname $0)

df -h

TARGET_DIR=REMOVED/$(date +%Y-%m-%d)
mkdir -p $TARGET_DIR

echo === Started cleanup ===    
./cleanup.py files $TARGET_DIR
echo === du REMOVED TODAY ===
du -hc $TARGET_DIR
echo === du REMOVED ===         
du -hc REMOVED                  

du -h files

rm -rf REMOVED

df -h
