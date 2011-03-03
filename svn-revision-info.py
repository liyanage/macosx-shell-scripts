#!/usr/bin/env python
#
# Takes a list of SVN revision numbers on stdin and an SVN base URL as argument.
# Looks up the commit message for each revision and prints a line with revision number and message.
#
# Intended usage is with the output of svn mergeinfo:
# 
#     svn mergeinfo --show-revs eligible svn_url_1 svn_url_2 | svn-revision-info.py svn_base_url
#
# Written by Marc Liyanage <http://www.entropy.ch>
# 

import subprocess, sys, re, xml.etree.ElementTree

if len(sys.argv) < 2:
	print >> sys.stderr, 'Usage: {0} svn_base_url < file_with_list_of_revisions'.format(sys.argv[0])
	sys.exit(1)

svn_base_url = sys.argv[1]

for line in sys.stdin:
	line = line.strip()
	match = re.search('(\d+)', line)
	if not match:
		continue
	
	revision = match.group(0)
	cmd = 'svn log -l 1 --xml {0}@{1}'.format(svn_base_url, revision)
	popen = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
	output = popen.communicate()[0]
	if popen.returncode:
		print >> sys.stderr, 'Nonzero exit status for "{0}"'.format(cmd)
		continue
		
	tree = xml.etree.ElementTree.fromstring(output)
	msg = tree.find('logentry').findtext('msg')
	msg = ' '.join(msg.strip().splitlines())
	truncated = msg[:100]
	if len(truncated) < len(msg):
		truncated += ' [...]'
	msg = '{0}   {1}'.format(line, truncated.encode('utf-8'))
	print msg
