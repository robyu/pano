#!/bin/bash

#
# use this script to start the dockers manually (i.e. not using docker-compose)
# for debugging
#
export TZ=America/Los_Angeles && \
export LOCAL_IP=192.168.2.8 && \
export PANO_WWW=/mnt/HD2/pano/www && \
export PANO_FTP=/mnt/HD2/pano/FTP && \
export PANO_DERIVED=/mnt/HD2/pano/derived && \
export PANO_LOG=/mnt/HD2/pano/logs
export PANO_DEVELOP=/home/ryu/2020/pano-docker/pano

export IMAGE_PANO=pano-docker_pano
export IMAGE_FTP=pano-docker_vsftpd
export IMAGE_WWW=pano-docker_lighttpd

#
# stop any running containers
#############################
docker stop  $(docker ps -q --filter ancestor="$IMAGE_PANO")
docker stop  $(docker ps -q --filter ancestor="$IMAGE_FTP")
docker stop  $(docker ps -q --filter ancestor="$IMAGE_WWW")
echo y | docker container prune

#
# start containers
###########################3
#
# these containers will run in the background
docker run -d -p 21:21 -p21100-21110:21100-21110 -v "$PANO_FTP":/home/ftpupload -v "$PANO_LOG":/var/log/vsftpd --env PASV_ADDRESS="$LOCAL_IP" --name vsftpd "$IMAGE_FTP" 

docker run -d  -v "$PANO_WWW":/var/www/localhost/htdocs -v "$PANO_FTP":/var/FTP -v "$PANO_DERIVED":/var/derived -v "$PANO_LOG":/var/log -p 8080:80 --name lighttpd "$IMAGE_WWW" 

#
# COMMENT ONE OF FOLLOWING TWO LINES:
#
# RUN DOCKER AND RETURN (normal mode)
docker run -d -v "$PANO_WWW":/var/www -v "$PANO_FTP":/var/FTP -v "$PANO_DERIVED":/var/derived  -v "$PANO_LOG":/home/pano/logs --name pano "$IMAGE_PANO"

# for debugging, you can run the pano docker interactively and stay attached
# also, /home/pano/develop should be mapped to the ./pano code directrory
# docker run -it -v "$PANO_WWW":/var/www \
#                -v "$PANO_FTP":/var/FTP \
#                -v "$PANO_DERIVED":/var/derived \
# 	       -v "$PANO_LOG":/home/pano/logs \
# 	       -v "$PANO_DEVELOP":/home/pano/develop \
# 	       --name pano --entrypoint=/bin/bash "$IMAGE_PANO"



