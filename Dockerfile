# ubuntu:latest maps to latest LTS
FROM phusion/baseimage:latest

ENV www_dir /www
ENV ftp_dir /FTP
ENV log_dir /var/log

RUN add-apt-repository -y ppa:deadsnakes/ppa

RUN apt update
RUN apt install -y nano 
RUN apt install -y ffmpeg
RUN apt install -y python3.7
RUN apt install -y sqlite3
RUN apt install -y python3-pip
RUN apt install -y imagemagick

#
# make python3.7 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1

RUN python3.7 -m pip install --upgrade pip
RUN python3.7 -m pip install dtutils click pudb
RUN groupadd -r pano && useradd --no-log-init -r -m -g pano pano


COPY *.py   /home/pano/
COPY *.json /home/pano/
     
RUN mkdir ${ftp_dir}
RUN chmod ugo+rw ${ftp_dir}
VOLUME ${ftp_dir}

RUN mkdir ${www_dir}
RUN chmod ugo+rw ${www_dir}
VOLUME ${www_dir}

RUN chmod ugo+rw ${log_dir}
VOLUME ${log_dir}

WORKDIR /home/pano
USER pano

CMD ["/bin/bash"]


