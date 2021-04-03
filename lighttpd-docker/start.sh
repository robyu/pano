#!/bin/sh

#
# still needed?
chmod a+w /dev/pts/0

ln -svf /var/FTP     /var/www/localhost/htdocs/FTP
ln -svf /var/derived /var/www/localhost/htdocs/derived

exec lighttpd -D -f /etc/lighttpd/lighttpd.conf
