# Dockerfile for lighttpd

FROM alpine

ENV LIGHTTPD_VERSION=1.4.54-r0

RUN apk add --update --no-cache \
	lighttpd=${LIGHTTPD_VERSION} \
	lighttpd-mod_auth \
        apache2-utils \
	bash \
  && rm -rf /var/cache/apk/*

#
# fix timezone
# see https://serverfault.com/questions/683605/docker-container-time-timezone-will-not-reflect-changes
RUN apk add --no-cache tzdata
ENV TZ America/Los_Angeles

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
# see https://vsupalov.com/docker-shared-permissions/
ARG USER_ID
ARG GROUP_ID
RUN addgroup -g $GROUP_ID www
#
# -D = no password
RUN adduser -G www -D -u $USER_ID www

COPY etc/lighttpd/* /etc/lighttpd/
COPY start.sh /usr/local/bin/
EXPOSE 80

VOLUME /var/www/localhost
VOLUME /etc/lighttpd

RUN mkdir /var/FTP
VOLUME /var/FTP

RUN mkdir /var/derived
VOLUME /var/derived

VOLUME /var/log

CMD ["start.sh"]
