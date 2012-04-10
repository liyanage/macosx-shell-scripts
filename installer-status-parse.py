#!/usr/bin/env python

import sys, re

percentage = 0
while True:
	line = sys.stdin.readline()
	if not line:
		break
		
	match = re.match(r'installer:(.+)', line)
	if not match:
		sys.stdout.write(line)
		continue

	line = match.group(1).strip().replace('PHASE:', '')
	match = re.match(r'%(.+)', line)
	if match:
		percentage = int(float(match.group(1)))
	else:
		status = line
	
	sys.stdout.write('\x1b[0G\x1b[0K')
	sys.stdout.write(' {0: >3d}%  {1}'.format(percentage, status))
	sys.stdout.write('\x1b[0G')
	sys.stdout.flush()

print
