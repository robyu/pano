#!/bin/bash

#
# stop containers
##################
docker stop lighttpd
docker stop vsftpd
docker stop pano

# delete containers
######################
docker rm lighttpd
docker rm vsftpd
docker rm pano

