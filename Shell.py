
import subprocess, sys
import xml.etree.ElementTree

class Shell:

	def __init__(self, fatal = False, verbose = False):
		self.fatal = fatal
		self.verbose = verbose
		self.reset()
	
	def reset(self):
		self.xml = None
		self.plist = None
	
	def run(self, command, silent = False):
		self.reset()
		command_is_string = isinstance(command, basestring)
		popen = subprocess.Popen(command, stderr = subprocess.PIPE, stdout = subprocess.PIPE, shell = command_is_string)
		(self.output, self.stderr) = popen.communicate()
		self.returncode = popen.returncode

		should_log_failure = self.returncode and self.fatal

		if self.verbose or should_log_failure:
			if not command_is_string:
				command = ' '.join(command)
			
		if self.verbose and not should_log_failure:
			print "running shell command:", command
			
		if should_log_failure:
			print >> sys.stderr, 'Non-zero exit status {0} for command "{1}": {2}'.format(self.returncode, command, self.stderr)
			sys.exit(1)
		
		if self.stderr and not silent:
			print >> sys.stderr, self.stderr
		
		return self

	def output_strip(self):
		return self.output.strip()

	def output_xml(self):
		if not self.xml:
			self.xml = xml.etree.ElementTree.fromstring(self.output)
		return self.xml
	
	def output_plist(self):
		if not self.plist:
			self.plist = plistlib.readPlistFromString(self.output)
		return self.plist
