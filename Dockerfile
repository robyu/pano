# ubuntu:latest maps to latest LTS
#
# docker build -t imagename:00 .
# docker run -t -d  -v /Users/chuyu/Documents/2020/docker-pano/pano:/home/pano  mypano:13
# docker exec -it -u root agitated_joliot /bin/bash
#
FROM phusion/baseimage:latest

ENV www_dir /var/www
ENV ftp_dir /var/FTP
ENV log_dir /home/pano/logs
ENV derived_dir /var/derived

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
     
RUN mkdir ${ftp_dir}
RUN chmod -R ugo+rw ${ftp_dir}
VOLUME ${ftp_dir}

RUN mkdir ${www_dir}
RUN mkdir ${www_dir}/css
RUN mkdir ${www_dir}/fonts
RUN mkdir ${www_dir}/js
RUN chmod -R ugo+rw ${www_dir}
COPY www        ${www_dir}/
COPY www/css    ${www_dir}/css/
COPY www/fonts  ${www_dir}/fonts/
COPY www/js     ${www_dir}/js/
VOLUME ${www_dir}

RUN mkdir ${derived_dir}
RUN chmod ugo+rw -R ${derived_dir}
VOLUME ${derived_dir}

COPY *.py   /home/pano/
COPY *.json /home/pano/
RUN chown -R pano:pano /home/pano
VOLUME /home/pano

RUN mkdir ${log_dir} 
#RUN chmod ugo+rw -R ${log_dir}
VOLUME ${log_dir}

USER pano
WORKDIR /home/pano


CMD ["/bin/bash"]


