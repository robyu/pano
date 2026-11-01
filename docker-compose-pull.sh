#!/bin/bash

docker login

source docker-compose-setup.sh

pano_compose pull lighttpd vsftpd pano

docker images --filter=reference='robyu/pano*'

