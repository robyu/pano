#!/bin/bash

#
# copy local www files into /var/www
cp -r -f /home/pano/www/css        /var/www/.
cp -r -f /home/pano/www/fonts      /var/www/.
cp -r -f /home/pano/www/js         /var/www/.
cp -r -f /home/pano/www/mryuck.png /var/www/.

python3 pano.py --loglevel info --logfname pano.log  pano-chuyu-server.json
