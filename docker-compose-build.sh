#!/bin/bash

source docker-compose-setup.sh

docker-compose build

docker images --filter=reference='robyu/pano*'

