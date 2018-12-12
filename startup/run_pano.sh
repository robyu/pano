#!/bin/bash

#
# run by pano.service
#
# use "systemctl status pano" to view status
# 
cd /home/pi/pano
./pano.py pano-ry.json &
./watchdog.py pano-ry.json &
