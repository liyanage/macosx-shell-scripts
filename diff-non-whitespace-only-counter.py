#!/usr/bin/env python
#
# Find change lines in a unified diff that are not just leading whitespace changes
#

import collections
import sys
import re

counter = collections.Counter()

with open(sys.argv[1]) as f:
    for line in f:
        if not line:
            continue
        operation = line[0]
        if operation not in '+-':
            continue
        
        content = line[1:]
        content = re.findall(r'^\s*(\S.*)$', content)
        if not content:
            continue
        content = content[0]
        if operation == '-':
            counter[content] -= 1
        elif operation == '+':
            counter[content] += 1


for key, count in counter.iteritems():
    if not count:
        continue
    
    print key