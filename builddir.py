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
import collections

class Tool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        cmd = ['osascript', '-e', 'tell application "Xcode" to path of document of window 1']
        try:
            output = subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            print('Unable to get path of frontmost Xcode document, make sure it is a project or workspace window and Xcode is not hidden', file=sys.stderr)
            return 1

        path = output.strip()
        _, extension = os.path.splitext(path)
        if extension == '.xcworkspace':
            cmd = ['osascript', '-e', 'tell application "Xcode" to name of active scheme of document of window 1']
            try:
                output = subprocess.check_output(cmd).strip()
            except subprocess.CalledProcessError as e:
                print('Unable to get scheme of frontmost Xcode document', file=sys.stderr)
                return 1
            scheme = output
            options = ['-scheme', scheme, '-workspace', path]
        elif extension == '.xcodeproj':
            options = ['-project', path]
        else:
            print('Unable to determine type of frontmost Xcode document with path "{}"'.format(path), file=sys.stderr)
            return 1

        cmd = ['xcodebuild', '-configuration', 'Debug', '-showBuildSettings'] + options
        print('running "{}"'.format(' '.join(cmd)))

        output = subprocess.check_output(cmd)
        pairs = re.split(r'^Build settings for action build and target (.+?):$', output, flags=re.MULTILINE)
        del pairs[0]
        all_settings = collections.defaultdict(dict)
        for i in range(0, len(pairs), 2):
            target, settings = pairs[i:i + 2]
            for key, value in re.findall(r'^\s+(\w+)\s+=[ \t]*(.*)$', settings, flags=re.MULTILINE):
                all_settings[target][key] = value
        
        build_dir = all_settings.items()[0][1]['BUILT_PRODUCTS_DIR']
        print(build_dir)
        cmd = ['open', build_dir]
        subprocess.check_call(cmd)

        return 0

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Description')
        # parser.add_argument('path', help='Path to something')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        return cls(args).run()


if __name__ == "__main__":
    sys.exit(Tool.main())
