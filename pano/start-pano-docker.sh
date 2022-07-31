#!/bin/bash

#
# this is the entry script for the pano docker

#
# copy local www files into working www dir
CP=/bin/cp
$CP -rfv /home/pano/www/* /var/www/

#
# set up symbol links from www directory to elsewhere
ln -s /var/derived /var/www/derived
ln -s /var/FTP     /var/www/FTP

python3 pano.py --loglevel info --logfname /home/pano/logs/pano.log --nodroptable  pano-docker.json
