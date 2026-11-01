#!/bin/bash

source docker-compose-setup.sh

pano_compose build

docker images --filter=reference='robyu/pano*'

