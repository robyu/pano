#!/bin/bash

#
# add this to /etc/rc.local
#
# /home/pi/pano/startup/run_pano.sh | /usr/bin/logger
#
LOGGER=/usr/bin/logger

echo "starting run_pano.sh"

cd /home/pi/pano
if pgrep -f "pano.py" > /dev/null
then
    echo "pano.py already running"
else
    echo "starting pano.py"
    ./pano.py pano-ry.json &
fi

if pgrep -f "watchdog.py" > /dev/null
then
    echo "watchdog.py already running"
else
    echo "starting watchdog"
    ./watchdog.py pano-ry.json &
fi

echo "finished run_pano.sh"
