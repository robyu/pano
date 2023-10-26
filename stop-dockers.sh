#!/bin/bash

#
# stop containers
##################
docker stop lighttpd
docker stop vsftpd
docker stop pano

# delete containers
######################
echo y | docker container prune

