#!/bin/bash

export TZ=America/Los_Angeles && \
export LOCAL_IP=192.168.2.8 && \
export PANO_WWW=/mnt/HD2/pano/www && \
export PANO_FTP=/mnt/HD2/pano/FTP && \
export PANO_DERIVED=/mnt/HD2/pano/derived && \
export PANO_LOG=/mnt/HD2/pano/logs

#
# start containers
###########################3
#read  -n 1 -p "type enter to run containers:" mainmenuinput

docker run -d -p 21:21 -p21100-21110:21100-21110 -v "$PANO_FTP":/home/ftpupload -v "$PANO_LOG":/var/log/vsftpd --env PASV_ADDRESS="$LOCAL_IP" --name vsftpd pano-docker_vsftpd

docker run -d -t -v "$PANO_WWW":/var/www/localhost/htdocs -v "$PANO_FTP":/var/FTP -v "$PANO_DERIVED":/var/derived -v "$PANO_LOG":/var/log -p 8080:80 --name lighttpd pano-docker_lighttpd


#
# COMMENT ONE OF FOLLOWING TWO LINES:
#
# RUN DOCKER AND RETURN (normal mode)
#docker run -d -v "$PANO_WWW":/var/www -v "$PANO_FTP":/var/FTP -v "$PANO_DERIVED":/var/derived  -v "$PANO_LOG":/home/pano/logs --name pano pano

# for debugging, you can run the pano docker directly and stay attached:
docker run -it -v "$PANO_WWW":/var/www -v "$PANO_FTP":/var/FTP -v "$PANO_DERIVED":/var/derived  -v "$PANO_LOG":/home/pano/logs --name pano-docker_pano /bin/bash


