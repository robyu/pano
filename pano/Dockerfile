# pano application image
#
# docker build -t imagename:00 .
#
# Base is the official Python image pinned by digest (Python 3.14.x on Debian trixie).
FROM python:3.14-slim-trixie@sha256:cd89c30eda26ee911a4611b18680086e0ea42e6f5f8cbe653d07fa7958c9cec8

ENV www_dir=/var/www
ENV ftp_dir=/var/FTP
ENV derived_dir=/var/derived
ENV log_dir=/home/pano/logs

ENV TZ=America/Los_Angeles
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

#
# runtime tools: ffmpeg (video), imagemagick (thumbnails), sqlite3,
# tzdata, ca-certificates; procps provides pgrep for the healthcheck.
#
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        imagemagick \
        nano \
        procps \
        sqlite3 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

#
# set timezone (must happen after tzdata is installed)
#
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

#
# python deps (dtutils is the local /home/pano/dtutils.py, not the PyPI package)
#
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

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
COPY --chown=pano:pano start-pano-docker.sh /home/pano

#
# for www files such as css, fonts, etc.
# we need to copy the files into the container,
# then symlink the files into /var/www once pano starts (see start-pano-docker.sh)
#
COPY --chown=pano:pano www/       /home/pano/www/

#
# note: pano-docker.json is NOT baked into the image. It is bind-mounted
# read-only at /home/pano/pano-docker.json (see docker-compose.yml).
#
# Do NOT declare VOLUME /home/pano here: an anonymous volume would mask the
# code COPYed into the image and survive image upgrades. Only /home/pano/logs
# and /home/pano/develop are volumes.
#
RUN mkdir ${log_dir}
VOLUME ${log_dir}

WORKDIR /home/pano

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD pgrep -f "[p]ython3 pano.py" >/dev/null || exit 1

CMD ["./start-pano-docker.sh"]
