#!/bin/sh
#
# add leading zeros to single-digit photo files.

for i in ?\ D*; do mv "$i" "0$i"; done

