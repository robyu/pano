#!/bin/bash

DIR_WWW=$1
DIR_FTP=$2
DIR_DERIVED=$3

# if FTP and derived directories are located under /media/wd2tb,
# then set up symlinks in the www directory as follows:   
# want the www to look like this:
# /var/www
#         ./FTP      -> /media/wd2tb/FTP
#         ./derived  -> /media/wd2tb/derived
#   	  ./js       -> ~/pano/www/js
# 	  ./css      -> ~/pano/www/css

ln -sf $DIR_WWW/FTP/ $DIR_FTP
ln -sf $DIR_WWW/derived $DIR_DERIVED
ln -sf $DIR_WWW/js/ ./www/js
ln -sf $DIR_WWW/css ./www/css

ls -als $DIR_WWW

