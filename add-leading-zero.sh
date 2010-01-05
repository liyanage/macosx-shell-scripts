#!/bin/sh
#
# add leading zeros to single-digit photo files.

for i in ?\ *.jpg; do mv "$i" "0$i"; done
for i in ??\ *.jpg; do mv "$i" "0$i"; done

