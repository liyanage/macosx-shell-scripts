#!/usr/bin/env python
#
# dump the contents of all toplevel keys in scutil's toplevel list.
#

import subprocess
import re

def run_command_with_input(command, input):
    popen = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (stdout, stderr) = popen.communicate(input)
    return stdout

scutil_script = 'list\n'
stdout = run_command_with_input('/usr/sbin/scutil', scutil_script)
keys = re.findall(r'subKey \[\d+\] = (.+)', stdout)

for key in keys:
    scutil_script = 'show {}\n'.format(key)
    print '\n====== {} ======'.format(key)
    print run_command_with_input('/usr/sbin/scutil', scutil_script)
    
