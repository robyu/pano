#!/bin/bash

DIR_WWW=$1
DIR_FTP=$2
DIR_DERIVED=$3

ln -sf $DIR_WWW/FTP/ $DIR_FTP
ln -sf $DIR_WWW/derived $DIR_DERIVED
ln -sf $DIR_WWW/js/ ./www/js
ln -sf $DIR_WWW/css ./www/css


