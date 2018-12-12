PWD=`pwd`
ln -s $PWD/pano.service /lib/systemd/system/pano.service
chmod 644 /lib/systemd/system/pano.service
systemctl daemon-reload
systemctl enable pano.service
