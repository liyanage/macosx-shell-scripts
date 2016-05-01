#!/usr/bin/env python
#
# Takes a list of SVN revision numbers on stdin and an SVN base URL as argument.
# Looks up the commit message for each revision and prints a line with revision number and message.
#
# Intended usage is with the output of svn mergeinfo:
# 
#     svn mergeinfo --show-revs eligible svn_url_1 svn_url_2 | svn-revision-info.py svn_base_url
#
# or alternatively with two SVN URLs, in which case the script runs "svn mergeinfo" for you
# and figures out the base URL automatically:
# 
#     svn-revision-info.py svn_url_1 svn_url_2
#
# Written by Marc Liyanage <http://www.entropy.ch>
# 

import subprocess, sys, re, xml.etree.ElementTree
from pprint import pprint

svn_url_src = ''
svn_url_dst = ''
svn_base_url = ''

argc = len(sys.argv)
if argc == 3:
	svn_url_src, svn_url_dst = sys.argv[1:3]
elif argc == 2:
	svn_base_url = sys.argv[1]
	input_lines = [line.rstrip() for line in sys.stdin]
else:
	print >> sys.stderr, 'Usage:'
	print >> sys.stderr, '{0} svn_base_url < file_with_list_of_revisions'.format(sys.argv[0])
	print >> sys.stderr, '{0} svn_url_source svn_url_destination'.format(sys.argv[0])
	exit(1)

if svn_url_src:
	cmd = 'svn mergeinfo --show-revs eligible "{0}" "{1}"'.format(svn_url_src, svn_url_dst)
	popen = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
	output = popen.communicate()[0]
	if popen.returncode:
		print >> sys.stderr, 'Nonzero exit status for "{0}"'.format(cmd)
		exit(1)
	input_lines = output.split()
	
	cmd = 'svn info --xml "{0}"'.format(svn_url_src)
	popen = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
	output = popen.communicate()[0]
	if popen.returncode:
		print >> sys.stderr, 'Nonzero exit status for "{0}"'.format(cmd)
		exit(1)

	tree = xml.etree.ElementTree.fromstring(output)
	svn_base_url = tree.findtext('entry/repository/root')


for line in input_lines:
	match = re.search('(\d+)', line)
	if not match:
		if re.match('^\s*$', line):
			print line
		continue
	
	revision = match.group(0)
	cmd = 'svn log -l 1 --xml {0}@{1}'.format(svn_base_url, revision)
	popen = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
	output = popen.communicate()[0]
	if popen.returncode:
		print >> sys.stderr, 'Nonzero exit status for "{0}"'.format(cmd)
		continue

	tree = xml.etree.ElementTree.fromstring(output)
	author = tree.find('logentry').findtext('author')
	msg = tree.find('logentry').findtext('msg')
	msg = ' '.join(msg.strip().splitlines())
	truncated = msg[:100]
	if len(truncated) < len(msg):
		truncated += ' [...]'
	msg = '{0} [{1:<10}]  {2}'.format(line, author[0:10], truncated.encode('utf-8'))
	print msg
