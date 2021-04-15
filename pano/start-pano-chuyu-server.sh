#!/bin/bash


#
# copy local www files into working www dir
CP=/usr/bin/cp
$CP -rfv -f www/ /mnt/HD2/pano/www

python3 pano.py --loglevel info --logfname /mnt/HD2/pano/logs/pano.log  --nodroptable pano-chuyu-server.json
