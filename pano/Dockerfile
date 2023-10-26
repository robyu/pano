# ubuntu:latest maps to latest LTS
#
# docker build -t imagename:00 .
# docker run -t -d  -v /Users/chuyu/Documents/2020/docker-pano/pano:/home/pano  mypano:13
# docker exec -it -u root agitated_joliot /bin/bash
#
#FROM phusion/baseimage:master-amd64
FROM phusion/baseimage:focal-1.0.0

ENV www_dir /var/www
ENV ftp_dir /var/FTP
ENV derived_dir /var/derived
ENV log_dir /home/pano/logs

RUN add-apt-repository -y ppa:deadsnakes/ppa
RUN apt update

RUN apt install -y nano 
RUN apt install -y ffmpeg
RUN apt install -y python3.7
RUN apt install -y python3.7-distutils # https://askubuntu.com/questions/1239829/modulenotfounderror-no-module-named-distutils-util
RUN apt install -y sqlite3
RUN apt install -y python3-pip
RUN apt install -y imagemagick

###################
# set timezone
# see https://serverfault.com/questions/683605/docker-container-time-timezone-will-not-reflect-changes
# and https://stackoverflow.com/questions/44331836/apt-get-install-tzdata-noninteractive
#

# need to set the symbolic link BEFORE installing tzdata!!!
# otherwise tzdata sets the timezone to Etc/UTC
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
# make tzdata installation non-interactive
ENV DEBIAN_FRONTEND=noninteractive
RUN apt install -y tzdata

#
# make python3.7 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1

RUN python3.7 -m pip install --upgrade pip
RUN python3.7 -m pip install dtutils
RUN python3.7 -m pip install click
RUN python3.7 -m pip install pudb

#
# match user id and group id with host
#
# see https://vsupalov.com/docker-shared-permissions/
ARG USER_ID
ARG GROUP_ID

RUN groupadd -r --gid $GROUP_ID pano
RUN useradd --uid $USER_ID --gid $GROUP_ID -ms /bin/bash pano

RUN mkdir ${ftp_dir}
VOLUME ${ftp_dir}

RUN mkdir ${derived_dir}
VOLUME ${derived_dir}

RUN mkdir ${www_dir}
VOLUME ${www_dir}

#
# THIS volume can be mapped to the actual development directory on the host
# so I can make changes on the code and see them in the container
RUN mkdir /home/pano/develop
VOLUME /home/pano/develop
###############
# remaining operations are done as user 'pano'
USER pano

COPY --chown=pano:pano *.py          /home/pano/
COPY --chown=pano:pano *.json        /home/pano/
COPY --chown=pano:pano start-pano-docker.sh /home/pano

#
# for www files such as css, fonts, etc.
# we need to copy the files into the container,
# then symlink the files into /var/www once pano starts (see start-pano.sh)
#
COPY --chown=pano:pano www/       /home/pano/www/

VOLUME /home/pano

RUN mkdir ${log_dir} 
#RUN chmod ugo+rw -R ${log_dir}
VOLUME ${log_dir}

WORKDIR /home/pano


CMD ["./start-pano-docker.sh"]



