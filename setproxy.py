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
    
def interface_list():
    return subprocess.check_output('networksetup -listallnetworkservices'.split()).splitlines()[1:]

def first_interface():
    return interface_list()[0]


first_interface = first_interface()

state = proxy_state_for_interface(first_interface)
if state['Enabled'] == 'Yes':
    print 'Disabling proxy...'
    disable_proxy_for_interface(first_interface)
else:
    print 'Enabling proxy...'
    enable_proxy_for_interface(first_interface)