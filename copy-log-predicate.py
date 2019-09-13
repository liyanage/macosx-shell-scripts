#!/usr/bin/env python


from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division
from __future__ import print_function

import sys
import os
import re
import argparse
import logging
import subprocess


class Tool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        with open(os.path.expanduser('~/.logrc')) as x: logrc = x.read()

        sections = re.split(r'^(\w+):', logrc, flags=re.MULTILINE)
        del(sections[0])
        while sections:
            key, value = sections.pop(0), sections.pop(0)
            if key != 'predicate':
                continue

            aliases = re.split(r'^\s+(\w+)\s*$', value, flags=re.MULTILINE)
            del(aliases[0])
            while aliases:
                key, value = aliases.pop(0), aliases.pop(0)
                if key != self.args.predicate_alias:
                    continue
                concatenated = re.sub(r'\s*$\s*', '', value, flags=re.MULTILINE)
                print(concatenated)
                pbcopy_process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                pbcopy_process.stdin.write(concatenated)


    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Copy ~/.logrc predicates to clipboard')
        parser.add_argument('predicate_alias', help='Alias for the predicate to be used')
        return cls(parser.parse_args()).run()

if __name__ == "__main__":
    sys.exit(Tool.main())








