#!/bin/bash

export USERID=$(id -u)
export GROUPID=$(id -g)
export LOCAL_IP=192.68.2.8
export PANO_WWW=/mnt/HD2/pano/www
export PANO_FTP=/mnt/HD2/pano/FTP
export PANO_DERIVED=/mnt/HD2/pano/derived
export PANO_LOG=/mnt/HD2/pano/logs

#
# you first need to manually generate a passwd.digest file
# for mod_auth to work
cd lighttpd-docker
DIGEST=passwd.digest
if [[ ! -f "$DIGEST" ]]; then
   echo you need to create "$DIGEST"
   echo see Dockerfile
   return 1 2>/dev/null # this will attempt to return
   exit 1 # exits if return didnt work
fi
cd ..


#
# here we go...
USER_ID=$USERID \
      GROUP_ID=$GROUPID \
      PASV_ADDRESS=$LOCAL_IP \
      PANO_WWW=$PANO_WWW \
      PANO_FTP=$PANO_FTP \
      PANO_DERIVED=$PANO_DERIVED \
      PANO_LOG=$PANO_LOG \
      docker-compose up -d --build

