#!/bin/sh
# 
# Update Python 3
#

set -e
set -x


pkg_url=$(curl -s https://www.python.org/downloads/ | awk -F '"' '/Download Python 3/ && /pkg/ {print $4}')
echo $pkg_url

curl -o $TMPDIR/python3.pkg $pkg_url
sudo installer -pkg $TMPDIR/python3.pkg -target /
