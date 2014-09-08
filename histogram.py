#!/usr/bin/env python
#
# Print histogram of frequency of input lines
#
# Maintained at http://github.com/liyanage/macosx-shell-scripts
#

import sys
import fileinput
import subprocess
import collections

data = collections.Counter()
data.update(fileinput.input())
sorted_items = sorted(data.items(), cmp=lambda a, b: cmp(b[1], a[1]))
total_count = sum([x[1] for x in sorted_items])
print '{} item(s) total'.format(total_count)
if not total_count:
    sys.exit(0)

with open('/dev/tty') as tty:
    h, w = [int(x) for x in subprocess.check_output(['stty', 'size'], stdin=tty).split()]
    
max_bar_length = w / 2 - 12
scale = float(max_bar_length) / sorted_items[0][1]


for item, count in sorted_items:
    bar_length = int(scale * count)
    percentage = count * 100 / total_count
    print '{:{width}}  {:4} {:>3}% {}'.format(item.strip()[:w/2], count, percentage, '*' * bar_length, width=w / 2)
