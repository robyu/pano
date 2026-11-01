FROM almalinux:9@sha256:245f8aab832fe800aa42bdab5fad75ebbd8e0b4c9f24820a83c638b177857ae2

RUN dnf -y install nano openssl vsftpd && dnf clean all

#
# match user id and group id with host
#
# see https://vsupalov.com/docker-shared-permissions/
ARG USER_ID
ARG GROUP_ID

RUN groupadd --gid $GROUP_ID ftpupload
RUN useradd --uid $USER_ID --gid $GROUP_ID -ms /bin/bash ftpupload && echo 'ftpupload:upload' | chpasswd

# set timezone
# see https://serverfault.com/questions/683605/docker-container-time-timezone-will-not-reflect-changes
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone


COPY vsftp.conf /etc/vsftp/vsftp.conf
COPY vsftp_ftps.conf /etc/vsftp/vsftp_ftps.conf
COPY vsftp_ftps_tls.conf /etc/vsftp/vsftp_ftps_tls.conf
COPY vsftp_ftps_implicit.conf /etc/vsftp/vsftp_ftps_implicit.conf
COPY start.sh /

RUN chmod +x /start.sh
RUN mkdir -p /home/vsftpd/
#RUN chown -R ftp:ftp /home/vsftpd/

VOLUME /home/ftpupload
VOLUME /var/log/vsftpd

EXPOSE 20 21 21100-21110

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD timeout 5 bash -c '</dev/tcp/127.0.0.1/21' || exit 1

ENTRYPOINT ["/start.sh"]
