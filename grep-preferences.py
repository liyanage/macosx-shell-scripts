#!/usr/bin/env python
#
# Grep preferences plists
#
# Written by Marc Liyanage
#
# https://github.com/liyanage/macosx-shell-scripts
#

import argparse
import os
import re
import subprocess
import plistlib


class Tool(object):

    def __init__(self, search_string, exclude=None):
        self.search_string = search_string.lower()
        self.exclude = []
        if exclude:
            for item in exclude:
                self.exclude.append(item.lower())
    
    def run(self):
        for dir in ['/Library/Preferences', os.path.expanduser('~/Library/Preferences')]:
            self.process_directory(dir)
    
    def process_directory(self, directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if not file.endswith('.plist'):
                    continue
                
                did_print_file = False
                full_path = os.path.join(root, file)
                domain = full_path[:-6]
                if os.stat(full_path).st_size == 0:
                    print 'skipping zero-byte plist {}'.format(full_path)
                    continue
                    
                try:
                    xml_plist = subprocess.check_output(['sudo', 'plutil', '-convert', 'xml1', '-o', '-', full_path])
                    plist = plistlib.readPlistFromString(xml_plist)
                except Exception as e:
                    print 'Unable to read plist "{}": {}\n'.format(full_path, e)

                if not isinstance(plist, dict):
                    print 'Skipping non-dict plist of type {} in {}\n'.format(type(plist), full_path)
                    continue
                    
                for key, value in plist.items():
                    key_lower = key.lower()
                    is_excluded = False
                    if self.search_string in key_lower:
                        for exclude_item in self.exclude:
                            if exclude_item in key_lower:
                                is_excluded = True
                        if is_excluded:
                            continue
                        if not did_print_file:
                            did_print_file = True
                            print full_path
                        print u'{}: {}'.format(key, value)
                if did_print_file:
                    print ''

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Grep keys in preferences plist files for string')
        parser.add_argument('search_string', help='The search string')
        parser.add_argument('--exclude', action='append', help='Exclude matches that also match this string. Can be given multiple times')

        args = parser.parse_args()
        cls(search_string=args.search_string, exclude=args.exclude).run()


if __name__ == '__main__':
    Tool.main()