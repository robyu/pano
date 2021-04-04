#!/bin/bash

#
# copy local www files into working www dir
cp -rv -f www/ /mnt/HD2/pano/www

python3 pano.py --loglevel info --logfname stdout  --nodroptable pano-chuyu-server.json
