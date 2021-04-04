#!/bin/bash


#
# copy local www files into working www dir
CP=/usr/bin/cp
$CP -rfv -f www/ /mnt/HD2/pano/www

python3 pano.py --loglevel info --logfname stdout  --nodroptable pano-chuyu-server.json
