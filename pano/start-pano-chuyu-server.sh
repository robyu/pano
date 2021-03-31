#!/bin/bash

#
# copy local www files into working www dir
cp -r -f /home/pano/www/css        /mnt/HD2/pano/www/.
cp -r -f /home/pano/www/fonts      /mnt/HD2/pano/www/.
cp -r -f /home/pano/www/js         /mnt/HD2/pano/www/.
cp -r -f /home/pano/www/mryuck.png /mnt/HD2/pano/www/.

python3 pano.py --loglevel info --logfname stdout  --nodroptable pano-chuyu-server.json
