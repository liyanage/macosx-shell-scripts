#!/usr/bin/env python
#
# Helper tool to enable/disable OS X proxy and wrap mitmproxy
#
# https://github.com/liyanage/macosx-shell-scripts
# 

import subprocess
import re
import argparse

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

def toggle_proxy():
    service_name = primary_service_name()

    if proxy_enabled_for_service(service_name):
        disable_proxy_for_service(service_name)
    else:
        enable_proxy_for_service(service_name)

def wrap_mitmproxy():
    service_name = primary_service_name()

    if not proxy_enabled_for_service(service_name):
        enable_proxy_for_service(service_name)

    subprocess.check_call(['mitmproxy', '--palette', 'light'])

    if proxy_enabled_for_service(service_name):
        disable_proxy_for_service(service_name)

def main():
    parser = argparse.ArgumentParser(description='Helper tool for OS X proxy configuration and mitmproxy')
    parser.add_argument('--toggle', action='store_true', help='just toggle the proxy configuration')
    args = parser.parse_args()

    if args.toggle:
        toggle_proxy()
    else:
        wrap_mitmproxy()

if __name__ == '__main__':
    main()

