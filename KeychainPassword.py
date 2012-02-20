
import subprocess, re

class KeychainPassword:

	@classmethod
	def find_internet_password(cls, username, host = None):
		cmd = ['security', 'find-internet-password', '-g', '-a', username]
		if host:
			cmd.extend(['-s', host])
		
		return cls.run_security_command(cmd)
		
	@classmethod
	def find_generic_password(cls, username, label = None):
		cmd = ['security', 'find-generic-password', '-g', '-a', username]
		if label:
			cmd.extend(['-l', label])
		
		return cls.run_security_command(cmd)
		
	@classmethod
	def run_security_command(cls, cmd):
		securityProcess = subprocess.Popen(cmd, stderr = subprocess.PIPE, stdout = subprocess.PIPE)
		stdout, stderr = securityProcess.communicate()
		result = re.findall('password: "(.*)"', stderr)
		if not result:
			return None
		(password,) = result
		return password
