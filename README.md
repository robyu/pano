# pano-docker
pano + vsftpd + lighttpd

To build and run the three dockers, run the script
> docker-compose-up.sh

> (base) ryu@chuyu-server:pano-dev$ docker ps
> CONTAINER ID   IMAGE               COMMAND                  CREATED          STATUS          PORTS                                                              NAMES
> 420fc2a26bd5   pano-dev_vsftpd     "/start.sh"              13 minutes ago   Up 13 minutes   0.0.0.0:21->21/tcp, 20/tcp, 0.0.0.0:21100-21110->21100-21110/tcp   pano-dev_vsftpd_1
> 2708f86ae031   pano-dev_pano       "./start-pano-docker…"   13 minutes ago   Up 13 minutes                                                                      pano-dev_pano_1
> a5a52ee44230   pano-dev_lighttpd   "start.sh"               13 minutes ago   Up 13 minutes   0.0.0.0:8080->80/tcp                                               pano-dev_lighttpd_1

To monitor pano:
> tail -f /mnt/HD2/pano/logs/pano.log 

To bring things down:
> docker-compose down

