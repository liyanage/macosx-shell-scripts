#!/usr/bin/env python
#
# Toggles proxy on localhost on/off
#
# Recommended usage:
#
# sudo setproxy.py
#
# 

import subprocess
import re


def proxy_state_for_interface(interface):
    state = subprocess.check_output('networksetup -getwebproxy'.split() + [interface]).splitlines()
    return dict([re.findall(r'([^:]+): (.*)', line)[0] for line in state])

def enable_proxy_for_interface(interface):
    for subcommand in ['-setwebproxy', '-setsecurewebproxy']:
        subprocess.check_output(['networksetup', subcommand, interface, '127.0.0.1', '8080'])

def disable_proxy_for_interface(interface):
    for subcommand in ['-setwebproxystate', '-setsecurewebproxystate']:
        subprocess.check_output(['networksetup', subcommand, interface, 'Off'])
    
def first_interface():
    scutil_script = 'get State:/Network/Global/IPv4\nd.show\n'
    popen = subprocess.Popen('/usr/sbin/scutil', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (stdout, stderr) = popen.communicate(scutil_script)
    interface, = re.findall(r'PrimaryInterface\s*:\s*(.+)', stdout)

    order = subprocess.check_output('networksetup -listnetworkserviceorder'.split())
    mapping = re.findall(r'\(\d+\)\s(.*)$\n\(.*Device: (.+)\)$', order, re.MULTILINE)
    mapping = dict([(b, a) for (a, b) in mapping])
    
    service_name = mapping[interface]
    return service_name
    

first_interface = first_interface()

state = proxy_state_for_interface(first_interface)
if state['Enabled'] == 'Yes':
    print 'Disabling proxy on {}...'.format(first_interface)
    disable_proxy_for_interface(first_interface)
else:
    print 'Enabling proxy on {}...'.format(first_interface)
    enable_proxy_for_interface(first_interface)