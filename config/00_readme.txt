
USING MAC LAUNCHCTL TO LAUNCH SERVICES

configure mac to launch pano at startup with:
(as user ryu)
launchctl load org.robertyu.pano.plist

launchctl list | grep pano
-	-9	org.robertyu.pano

to launch the ftp server (pure-ftpd), you need
to configure as root:

launchctl load org.robertyu.pure-ftpd.plist



