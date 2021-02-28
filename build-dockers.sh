#!/bin/bash


# delete containers
######################
docker rm lighttpd
docker rm vsftpd
docker rm pano

#
# rebuild images
######################
cd docker-vsftpd
docker build -t vsftpd --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) .
cd ..

cd lighttpd-docker
#
# you first need to manually generate a passwd.digest file
# for mod_auth to work
DIGEST=passwd.digest
if [[ ! -f "$DIGEST" ]]; then
   echo you need to create "$DIGEST"
   echo see Dockerfile
   return 1 2>/dev/null # this will attempt to return
   exit 1 # exits if return didnt work
fi
docker build -t lighttpd --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g)   .
cd ..

cd pano
docker build -t pano  --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) .
cd ..

