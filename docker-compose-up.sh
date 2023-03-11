#!/bin/bash

source docker-compose-setup.sh

#
# here we go...
# --pull missing : build missing images
# --build : build image first
docker compose up -d 


