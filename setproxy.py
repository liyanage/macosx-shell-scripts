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

def run_networksetup_command(*arguments):
    return subprocess.check_output(['sudo', 'networksetup'] + list(arguments))

def proxy_state_for_service(service):
    state = run_networksetup_command('-getwebproxy', service).splitlines()
    return dict([re.findall(r'([^:]+): (.*)', line)[0] for line in state])

def enable_proxy_for_service(service):
    print 'Enabling proxy on {}...'.format(service)
    for subcommand in ['-setwebproxy', '-setsecurewebproxy']:
        run_networksetup_command(subcommand, service, '127.0.0.1', '8080')

def disable_proxy_for_service(service):
    print 'Disabling proxy on {}...'.format(service)
    for subcommand in ['-setwebproxystate', '-setsecurewebproxystate']:
        run_networksetup_command(subcommand, service, 'Off')

def interface_name_to_service_name_map():    
    order = run_networksetup_command('-listnetworkserviceorder')
    mapping = re.findall(r'\(\d+\)\s(.*)$\n\(.*Device: (.+)\)$', order, re.MULTILINE)
    return dict([(b, a) for (a, b) in mapping])

def run_command_with_input(command, input):
    popen = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (stdout, stderr) = popen.communicate(input)
    return stdout
    
def primary_interace_name():
    scutil_script = 'get State:/Network/Global/IPv4\nd.show\n'
    stdout = run_command_with_input('/usr/sbin/scutil', scutil_script)
    interface, = re.findall(r'PrimaryInterface\s*:\s*(.+)', stdout)
    return interface

def primary_service_name():
    return interface_name_to_service_name_map()[primary_interace_name()]

def proxy_enabled_for_service(service):
    return proxy_state_for_service(service)['Enabled'] == 'Yes'
    

def main():
    service_name = primary_service_name()

    if proxy_enabled_for_service(service_name):
        disable_proxy_for_service(service_name)
    else:
        enable_proxy_for_service(service_name)

if __name__ == '__main__':
    main()

