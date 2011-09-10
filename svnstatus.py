#!/usr/bin/env python
#
# Cleaned up "svn status" output
#

import subprocess

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
		continue

	if current_external:
		print current_external
		current_external = ''

	print line

	
