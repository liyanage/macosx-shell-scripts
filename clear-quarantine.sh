#!/bin/bash
#
# Remove the quarantine extended attribute from all
# developer documentation HTML files to get rid
# of the "downloaded from the Internet" warning
#
# Marc Liyanage / www.entropy.ch
#

[ $UID -eq 0 ] || { echo $0 must be run as root; exit 1; }

find /Developer -type f -name '*.html' | python <(cat - <<EOF
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
