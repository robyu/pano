#!/bin/bash
#tar xf testdata/FTP.tar.gz -C testdata/
rsync -a testdata/FTP.orig/         testdata/FTP
rsync -a testdata/FTP-culled.orig/  testdata/FTP-culled
