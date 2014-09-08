#!/usr/bin/env python
#
# Print histogram of frequency of input lines
#
# Maintained at http://github.com/liyanage/macosx-shell-scripts
#


import fileinput
import collections
import subprocess

data = collections.Counter()
data.update(fileinput.input())
sorted_items = sorted(data.items(), cmp=lambda a, b: cmp(b[1], a[1]))

with open('/dev/tty') as tty:
    h, w = [int(x) for x in subprocess.check_output(['stty', 'size'], stdin=tty).split()]
    
max_bar_length = w / 2 - 10
scale = float(max_bar_length) / sorted_items[0][1]

for location, count in sorted_items:
    bar_length = int(scale * count)
    print '{:{width}}  {:4}  {}'.format(location.strip()[:w/2], count, '*' * bar_length, width=w / 2)
