#!/usr/bin/env python

import subprocess, sys, xml.etree.ElementTree, datetime, optparse


def shell(cmd, fatal = True):
	popen = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE)
	output = popen.communicate()[0]
	if popen.returncode != 0:
		if fatal:
			sys.exit(1)
		else:
			return None
	return output


parser = optparse.OptionParser(usage = "Usage: %prog [options] svn_url")
parser.add_option("-v", dest = "verbose", help = "verbose", action="store_true")
(options, args) = parser.parse_args()
verbose = options.verbose


if len(args) > 0:
	svn_url = args[0]
else:
	# fall back to current directory if it is a sandbox
	cmd = 'svn info --xml'
	output = shell(cmd, False)
	if not output:
		parser.print_help()
		sys.exit(1)

	tree = xml.etree.ElementTree.fromstring(output)
	svn_url = tree.findtext('entry/url')


cmd = 'svn log --xml -v {0}'.format(svn_url)
popen = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE)
output = popen.communicate()[0]
if popen.returncode != 0:
	sys.exit(1)

tree = xml.etree.ElementTree.fromstring(output)

current_url_or_path = None
revision_count = 0

for logentry in tree.findall('logentry'):
	rev = logentry.get('revision')
	date = datetime.datetime.strptime(logentry.findtext('date')[:18], '%Y-%m-%dT%H:%M:%S')

	if not current_url_or_path:
		current_url_or_path = svn_url

	msg = logentry.findtext('msg')
	msg = ' '.join(msg.strip().splitlines())
	truncated = msg[:100]
	if len(truncated) < len(msg):
			truncated += ' [...]'
	msg = truncated.encode('utf-8')

	pathelement = logentry.find('paths/path')
	frompath = pathelement.get('copyfrom-path')
	path = pathelement.text
	if not (frompath and current_url_or_path.endswith(path)):
		revision_count += 1
		if verbose:
			print '                    r{0} {1}'.format(rev, msg)
		continue

	print '                    [{0} revisions]'.format(revision_count)
	revision_count = 0
	
	current_url_or_path = current_url_or_path.replace(path, frompath)
	fromrev = pathelement.get('copyfrom-rev')
	print '{0} r{1} created from {2}@{3}: {4}'.format(date, rev, current_url_or_path, fromrev, msg)

