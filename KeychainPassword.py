
import subprocess, re

class KeychainPassword:

    @classmethod
    def find_internet_password(cls, username, host=None):
        cmd = ['security', 'find-internet-password', '-g', '-a', username]
        if host:
            cmd.extend(['-s', host])
        
        username, password = cls.run_security_command(cmd)
        return password
        
    @classmethod
    def find_generic_password(cls, username, label=None):
        username, password = cls.find_generic_username_and_password(username=username, label=label)
        return password
        
    @classmethod
    def find_generic_username_and_password(cls, username=None, label=None):
        cmd = ['security', 'find-generic-password', '-g']
        if label:
            cmd.extend(['-l', label])
        if username:
            cmd.extend(['-a', username])
        return cls.run_security_command(cmd)

    @classmethod
    def run_security_command(cls, cmd):
        try:
            security_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except:
            return None
        
        result = re.findall('password: (?:0x([A-Z0-9]+)\s+)?"(.*?)"$.*"acct"<blob>="(.*?)"$', security_output, re.DOTALL|re.MULTILINE)
        if not result:
            return None
        (hexpassword, password, username), = result

        if hexpassword:
            password = hexpassword.decode('hex').decode('utf-8')

        return username, password

        
