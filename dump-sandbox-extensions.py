#!/usr/bin/env python
#
# Maintained at http://github.com/liyanage/macosx-shell-scripts/dump-sandbox-extensions.py
#


import sys
import os
import re
import tempfile
import time
import argparse
import logging
import ctypes
import subprocess
import collections


class DumpOutputParser(object):

    def __init__(self):
        self.linecount = 0
        self.state = 'start'
        self.setup_state_table()
        self.current_section = None
    
    def setup_state_table(self):
        Rule = collections.namedtuple('Rule', ['regex', 'new_state', 'action'])
        self.state_table = {
            'start': (
                Rule(re.compile('.*kernel\[0\] <Notice>: (.+)\[(\d+)\] unsandboxed'), None, 'stop_unsandboxed'),
                Rule(re.compile('.*kernel\[0\] <Notice>: (.+)\[(\d+)\] sandboxed {'), 'reading_body', None),
            ),
            'reading_body': (
                Rule(re.compile('.*kernel\[0\] <Notice>: - extensions \((.+)\) {'), 'reading_section', 'capture_section'),
                Rule(re.compile('.*kernel\[0\] <Notice>: - size ='), None, None),
                Rule(re.compile('.*kernel\[0\] <Notice>: }'), 'stopped', 'stop'),
            ),
            'reading_section': (
                Rule(re.compile('.*kernel\[0\] <Notice>: - }'), 'reading_body', None),
                Rule(re.compile('.*kernel\[0\] <Notice>:.*file: (.+) \(.*\); flags=.*'), None, 'capture_line'),
            )            
        }
    
    def update(self, line):
        self.linecount += 1
        if self.linecount > 10 and self.state == 'start':
            return False
        
        matched_rule = None
        for rule in self.state_table[self.state]:
            text_match = rule.regex.match(line)
            if not text_match:
                continue
            matched_rule = rule
            break
        
        if not matched_rule:
            raise Exception('No next state in state {} for line "{}"'.format(self.state, line))
        
        if matched_rule.new_state and self.state != matched_rule.new_state:
            self.state = matched_rule.new_state
        
        if matched_rule.action is None:
            pass
        elif matched_rule.action == 'stop_unsandboxed':
            print >> sys.stderr, '{}[{}] is unsandboxed'.format(text_match.group(1), text_match.group(2))
            return False
        elif matched_rule.action == 'start':
            pass
        elif matched_rule.action == 'stop':
            return False
        elif matched_rule.action == 'capture_line':
            if self.current_section:
                print '# {}'.format(self.current_section)
                self.current_section = None
            print '{}'.format(text_match.group(1))
        elif matched_rule.action == 'capture_section':
            self.current_section = text_match.group(1)
        else:
            raise Exception('Unknown action for input line "{}"'.format(line))
    
        return True


class Tool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        output = tempfile.TemporaryFile()
        syslog = subprocess.Popen(['syslog', '-w', '0', '-k', 'Facility', 'kern'], stdout=subprocess.PIPE)
        
        time.sleep(1)

        dump_result = self.request_dump()
        if dump_result:
            print >> sys.stderr, 'Unable to dump sandbox extensions for PID {}'.format(self.args.pid)
            return

        parser = DumpOutputParser()
        while parser.update(syslog.stdout.readline()):
            pass

        syslog.terminate()
            
    def request_dump(self):
        class PID(ctypes.Structure):
            _fields_ = [("pid", ctypes.c_int)]
        pid_struct = PID(self.args.pid)

        libsystem = ctypes.CDLL('/usr/lib/libSystem.dylib')
        syscall_func = getattr(libsystem, '__sandbox_ms')
        return syscall_func("Sandbox", 15, ctypes.pointer(pid_struct))

    @classmethod
    def ensure_superuser(cls):
        if os.getuid() != 0:
            os.execv('/usr/bin/sudo', ['/usr/bin/sudo'] + sys.argv)

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description="Dump kernel's bookmark / sandbox extension list for a process")
        parser.add_argument('pid', type=int, help='PID of process to inspect')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')

        args = parser.parse_args()
        cls.ensure_superuser()
        
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)
        
        cls(args).run()


if __name__ == "__main__":
    Tool.main()




