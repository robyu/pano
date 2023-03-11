# pano-docker
pano + vsftpd + lighttpd

## Running pano:
1. Pull images from docker hub:
> ./docker-compose-pull.sh

2. Start the dockers:
> ./docker-compose-up.sh

3. Stop the dockers:
> docker compose down


## Building the Images
1. Set the tag, e.g. "rel001", in docker-compose-setup.sh

2. Build:
> docker-compose-build.sh

## Pushing New Images to Docker Hub
git login
git push robyu/<image>:<imagetag>

## Viewing the Log

To monitor pano (other dockers write logs to the same directory)
> tail -F /mnt/HD2/pano/logs/pano.log 

## manually starting dockers
The scripts start-dockers.sh and stop-dockers.sh  are for starting the dockers "manually," without docker-compose. They're used when developing and testing.

## Project Log

https://docs.google.com/document/d/1UDShbouFjIxBU0mpFkE1or6D4iOpjN0G8gaLTpkIcR4/edit?usp=sharing
