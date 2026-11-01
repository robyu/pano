# Dockerfile for lighttpd
# see https://github.com/spujadas/lighttpd-docker/blob/master/Dockerfile

FROM alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc

ENV TZ=America/Los_Angeles

# bash for start.sh and debugging; tzdata for local time
RUN apk add --no-cache \
	bash \
	lighttpd \
	lighttpd-mod_auth \
	apache2-utils \
	nano \
	tzdata

## workaround for bug preventing sync between VirtualBox and host
# http://serverfault.com/questions/240038/lighttpd-broken-when-serving-from-virtualbox-shared-folder
RUN echo server.network-backend = \"writev\" >> /etc/lighttpd/lighttpd.conf

#
# add user to get mod_auth working
# 'authorized users only' must match 'realm' value in lighttpd.conf auth.require statement
#  htdigest -c passwd.digest 'authorized users only' ryu
COPY passwd.digest /etc/lighttpd/passwd.digest

#
# create www user and group
# match user id and group id with host
# see https://vsupalov.com/docker-uid-gid-overview/
ARG USER_ID
ARG GROUP_ID
RUN addgroup -g $GROUP_ID www
#
# -D: no password
RUN adduser -G www -D -u $USER_ID www

COPY etc/lighttpd/* /etc/lighttpd/
COPY start.sh /usr/local/bin/
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
	CMD nc -z 127.0.0.1 80 || exit 1

VOLUME /var/www/localhost
#VOLUME /etc/lighttpd

RUN mkdir /var/FTP
VOLUME /var/FTP

RUN mkdir /var/derived
VOLUME /var/derived

VOLUME /var/log

CMD ["start.sh"]
