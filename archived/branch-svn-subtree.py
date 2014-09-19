#!/usr/bin/env python

from Shell import Shell
import os, re, sys, argparse, urlparse


class ExternalsDefinition:

	def __init__(self, subdirectory, url):
		self.subdirectory = subdirectory
		self.url = url


class SVNDirectory:

	processed_locations = []

	def __init__(self, url, parent = None, replacements = None, workdir = None, commit_message = None):
		self.url = url
		self.parent = parent
		self._replacements = replacements
		self._subdirectories = None
		self._externals_property = None
		self._workdir = workdir
		self._commit_message = commit_message
	
	def workdir(self):
		return self.root()._workdir

	def commit_message(self):
		return self.root()._commit_message

	def commit_message_option(self):
		commit_message = self.commit_message()
		if not commit_message:
			return ''
		return "-m '{0}'".format(commit_message)
	
	def is_root(self):
		return not self.parent
		
	def root(self):
		if self.is_root():
			return self
		return self.parent.root()
	
	def subdirectories(self):
		if self._subdirectories == None:
			self._subdirectories = []
			contents_xml = Shell(verbose = False).run('svn ls --xml "{0}"'.format(self.url)).output_xml()
			for element in contents_xml.find('list').findall('entry'):
				if not element.get('kind') == 'dir':
					continue
				name = element.findtext('name')
				subdirectory_url = os.path.join(self.url, name)
				subdirectory = SVNDirectory(subdirectory_url, parent = self)
				if subdirectory.should_ignore():
					continue
				self._subdirectories.append(subdirectory)

		return self._subdirectories
	
	def should_ignore(self):
		if self.depth() > 2:
			return True
			
		name = self.name()
		for ignore in ('.lproj', '.nib', '.xcodeproj'):
			if name.find(ignore) != -1:
				return True
		return False
	
	def depth(self):
		if self.is_root():
			return 0
		return self.parent.depth() + 1
	
	def replacements(self):
		return self.root()._replacements
	
	def string_contains_replacement(self, string):
		for key in self.replacements():
			if string.find(key) != -1:
				return True
		return False

	def apply_replacements_to_string(self, string):
		replacements = self.replacements()
		for old in replacements:
			new = replacements[old]
			string = string.replace(old, new)
		return string
			
		for key in self.replacements().keys():
			if string.find(key) != -1:
				return True
		return False

	def externals_property(self):
		if self._externals_property == None:
			propget_cmd = Shell(verbose = False, fatal = True).run('svn pg --xml svn:externals "{0}"'.format(self.url))
			contents_xml = propget_cmd.output_xml()
			self._externals_property = contents_xml.findtext('target/property')
		return self._externals_property
	
	def externals_definitions(self):
		property = self.externals_property()
		externals = []
		for line in property.splitlines():
			match = re.search('("[^"]+"|\S+)\s+(.+)', line)
			if not match:
				continue
			directory = match.group(1).replace('"', '')
			url = match.group(2)
			externals.append(ExternalsDefinition(directory, url))
		return externals			
	
	def new_url(self):
		return self.apply_replacements_to_string(self.url)
	
	def new_name(self):
		return os.path.basename(self.new_url())
	
	def name(self):
		return os.path.basename(self.url)
	
	def sandbox_dir(self):
		if self.is_root():
			parsed_url = urlparse.urlparse(self.new_url())
			return os.path.join(self.workdir(), parsed_url.path[1:].replace('/', '-'))
		else:
			return os.path.join(self.parent.sandbox_dir(), self.new_name());

	def self_or_subdirectory_has_rewritten_externals(self):
		value = self.externals_property()
		if value and self.string_contains_replacement(value):
			return True

		for subdir in self.subdirectories():
			if subdir.self_or_subdirectory_has_rewritten_externals():
				return True
		
		return False
	
	def externals_urls_containing_replacements(self):
		urls = []
		for definition in self.externals_definitions():
			url = definition.url
			if self.string_contains_replacement(url):
				urls.append(url)
		return urls

	def process(self):
		
		new_url = self.new_url()

		if self.url in self.processed_locations:
#			print "### Skipping {0}, already processed".format(self.url)
			return False

		self.processed_locations.append(self.url)

 		if self.is_root():
 			print "###### processing as root dir"
			print 'svn cp {0} {1} {2}'.format(self.commit_message_option(), self.url, new_url)

		if not self.self_or_subdirectory_has_rewritten_externals():
			return False

		sandbox_dir = self.sandbox_dir()
		
		parent_dir = os.path.dirname(sandbox_dir)
		print 'cd {0}'.format(parent_dir)
		
 		if self.is_root():
			print 'svn co --depth empty {0} {1}'.format(self.new_url(), sandbox_dir)
		else:
			print 'svn up --depth empty {0}'.format(sandbox_dir)
		
		print 'cd {0}'.format(sandbox_dir)

		externals_value = self.externals_property()
		if externals_value and self.string_contains_replacement(externals_value):
			new_externals = self.apply_replacements_to_string(externals_value)
			print "svn ps svn:externals '{0}' .".format(new_externals)
			print "svn ci {0} .".format(self.commit_message_option())
			
			externals_urls_containing_replacements = [url for url in self.externals_urls_containing_replacements()]
			for url in externals_urls_containing_replacements:
				if url in self.processed_locations:
#					print "### Skipping externals URL {0}, already processed".format(url)
					continue
					
				print '### Processing external {0} in {1}'.format(url, self.url)
				externals_dir = SVNDirectory(url, replacements = self.replacements(), workdir = self.workdir(), commit_message = self.commit_message())
				externals_dir.process()
			
		for subdir in self.subdirectories():
			subdir.process()

		return True


class BranchMapper:

	def __init__(self, root_urls, replacements, commit_message = None):
		self.root_urls = root_urls
		self.replacements = replacements
		self.commit_message = commit_message
		self.prepare_workdir()
	
	def prepare_workdir(self):
		self.workdir = '-'.join((os.path.basename(sys.argv[0]), 'workdir'))
		if not os.path.exists(self.workdir):
			os.mkdir(self.workdir)
		self.workdir = os.path.abspath(self.workdir)
		os.chdir(self.workdir)
	
	def run(self):
		for root_url in self.root_urls:
 			print '### Processing toplevel URL {0}'.format(root_url)
			root_dir = SVNDirectory(root_url, replacements = self.replacements, workdir = self.workdir, commit_message = self.commit_message)
			root_dir.process()
	
	


parser = argparse.ArgumentParser(description = 'Branch subversion subtree')
parser.add_argument('--url', action = 'append', dest = 'root_urls', metavar = 'ROOT_URL', required = True, help='An SVN URL to be branched. Can be used multiple times.')
parser.add_argument('--replace', nargs = 2, action = 'append', metavar = 'REPLACEMENT', dest = 'replacements', required = True, help='a from -> to mapping of existing to new branch name. Can be used multiple times.')
parser.add_argument('-m', dest = 'commit_message', help='An optional SVN commit message')
args = parser.parse_args()
replacements = dict(args.replacements)

BranchMapper(args.root_urls, replacements, args.commit_message).run()

