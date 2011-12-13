#!/usr/bin/env python
#
# Cleaned up "svn status" output
#

import subprocess, time, sys

popen = subprocess.Popen(['svn', 'status'], stdout = subprocess.PIPE)
output = popen.communicate()[0]
if popen.returncode:
	sys.exit(1)

current_external = ''
for line in output.splitlines():
	
	if not len(line) or line.startswith('X'):
		continue

	if line.startswith('Performing status on external'):
		current_external = line
		print "\x1b[2K\r",
		print current_external,
		sys.stdout.flush()
		time.sleep(0.01)
		continue

	if current_external:
		current_external = ''
		print

	print line

print "\x1b[2K",
