#!/bin/bash

#
# this is the entry script for the pano docker

#
# copy local www files into working www dir
CP=/bin/cp
$CP -rfv /home/pano/www/* /var/www/

#
# set up symbol links from www directory to elsewhere
# -f : force/overwrite
# -v : verbose
ln -s -f -v /var/derived /var/www/derived
ln -s -f -v /var/FTP     /var/www/FTP

#
# run pano
#################3##
python3 pano.py --loglevel info --logfname /home/pano/logs/pano.log --nodroptable  pano-docker.json

#
# you can run pano.py in the debugger with
# python3 -m pudb pano.py ...
#
# python3 pano.py --loglevel info --logfname stdout --nodroptable  pano-docker-test.json
