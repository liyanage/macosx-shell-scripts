#!/bin/bash
#
# Remove the quarantine extended attribute from all
# developer documentation HTML files to get rid
# of the "downloaded from the Internet" warning
#
# Marc Liyanage / www.entropy.ch
#

[ $UID -eq 0 ] || { exec sudo $0; }

DIR="$1"
[ "$DIR" ] || { DIR=/Developer; echo no directory argument given, using $DIR; }

find "$DIR" -type f -name '*.html' | python <(cat - <<EOF
#!/usr/bin/env python

from xattr import *
import sys
import string

attr = 'com.apple.quarantine'

for file in sys.stdin:
	file = string.rstrip(file, "\n")
	if (attr in listxattr(file)):
		removexattr(file, attr)
EOF
)
