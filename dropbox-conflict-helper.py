#!/usr/bin/env python
#
# Dropbox conflict helper. To be run from within a BBEdit shell worksheet
#
# Written by Marc Liyanage
#
# https://github.com/liyanage/macosx-shell-scripts
#

import argparse
import os
import re
import subprocess


class Duplicate(object):

    def __init__(self, original_path):
        self.original_path = original_path
        self.duplicate_paths = []

    def add_duplicate_path(self, path):
        self.duplicate_paths.append(path)
    
    def summary(self):
        summary = subprocess.check_output(['ls', '-l', self.original_path])
        for duplicate_path in self.duplicate_paths:
            summary += subprocess.check_output(['ls', '-l', duplicate_path])
        return summary

    def worksheet(self):
        worksheet = ''
        for duplicate_path in self.duplicate_paths:
           worksheet += 'diff -u "{}" "{}"\n'.format(self.original_path, duplicate_path)
           worksheet += 'mv "{}" "{}"\n'.format(duplicate_path, self.original_path)
           worksheet += 'rm "{}"\n'.format(duplicate_path, self.original_path)
        return worksheet
    
    def __str__(self):
        return '<Duplicate {}>'.format(self.original_path)


class Tool(object):

    def __init__(self, dropbox_path):
        self.dropbox_path = os.path.expanduser(dropbox_path)
        assert os.path.exists(self.dropbox_path), 'Invalid Dropbox path {}'.format(dropbox_path)
        self.duplicates = []
        self.duplicate_map = {}
    
    def run(self):
        self.gather_duplicates()
        self.process_duplicates()
    
    def gather_duplicates(self):
        for root, dirs, files in os.walk(self.dropbox_path):
            for file in files:
                match = re.match(r'^(.+) \([^\(]+ conflicted copy .+\)(.*)$', file)
                if not match:
                    continue

                original_name = match.group(1)
                extension = match.group(2)
                if extension:
                    original_name += extension

                full_path = os.path.join(root, original_name)
                duplicate = self.duplicate_for_original_path(full_path)
                duplicate.add_duplicate_path(os.path.join(root, file))

    def process_duplicates(self):
        for duplicate in self.duplicates:
            print '# {}'.format(duplicate)
            print duplicate.summary()
            print duplicate.worksheet()
            print ''

    def duplicate_for_original_path(self, path):
        duplicate = self.duplicate_map.get(path, None)
        if not duplicate:
            duplicate = Duplicate(path)
            self.duplicates.append(duplicate)
            self.duplicate_map[path] = duplicate
        return duplicate

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Helper to process Dropbox conflict duplicates')
        parser.add_argument('dropbox_path', help='Path to Drobox folder')

        args = parser.parse_args()
        cls(dropbox_path=args.dropbox_path).run()


if __name__ == '__main__':
    Tool.main()