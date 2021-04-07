#!/bin/bash

#
# copy local www files into working www dir
CP=/bin/cp
$CP -rfv -f www/ /mnt/HD2/pano/www

python3 pano.py --loglevel info --logfname /home/pano/logs/pano.log --nodroptable  pano-docker.json
