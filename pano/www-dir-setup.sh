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
#   	  ./js       -> /users/ryu/pano/www/js
# 	  ./css      -> /users/ryu/pano/www/css
CWD=$(pwd)

ln -svf $DIR_FTP     $DIR_WWW/FTP
ln -svf $DIR_DERIVED $DIR_WWW/derived 
ln -svf "$CWD"/www/js  $DIR_WWW
ln -svf "$CWD"/www/css $DIR_WWW
cp www/mryuck.png      $DIR_WWW
ls -als $DIR_WWW

