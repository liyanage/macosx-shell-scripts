#!/usr/bin/env python


import sys
import os
import re
import argparse
import logging
import contextlib


class Tool(object):

    def __init__(self, args):
        self.args = args
        self.dry_run_cache = set()

    def run(self):
        for directory in self.args.source_directory:
            self.merge_directory(directory)

    def merge_directory(self, source_directory_root):
        source_directory_root = os.path.abspath(os.path.expanduser(source_directory_root))
        print 'Merging {} into {}'.format(source_directory_root, self.args.destination)
        for dirpath, dirnames, filenames in os.walk(source_directory_root):
            for filename in filenames:
                source_path = os.path.join(dirpath, filename)
                source_rel_path = os.path.relpath(source_path, start=source_directory_root)
                destination_path = os.path.join(self.args.destination, source_rel_path)
                destination_dir_path = os.path.dirname(destination_path)

                while os.path.exists(destination_path):
                    head, tail = os.path.splitext(destination_path)
                    number = 2
                    match = re.match(r'(.+)_(\d+)$', head)
                    if match:
                        number = int(match.group(2)) + 1
                        head = match.group(1)
                    new_destination_path = head + '_' + str(number) + tail
                    print '{} exists: {}'.format(destination_path, new_destination_path)
                    destination_path = new_destination_path

                if not os.path.exists(destination_dir_path):
                    if not self.is_dry_run('Create directory {}'.format(destination_dir_path), unique=True):
                        os.makedirs(destination_dir_path)

                if not self.is_dry_run('Link {} -> {}'.format(source_path, destination_path)):
                    os.link(source_path, destination_path)            

    def is_dry_run(self, description, unique=False):
        if self.args.dry_run:
            should_print = True
            if unique:
                if description in self.dry_run_cache:
                    should_print = False
                else:
                    self.dry_run_cache.add(description)
            if should_print:
                print 'Dry run: {}'.format(description)
        return self.args.dry_run

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Merge/Overlay directories')
        parser.add_argument('-d', '--destination', required=True, help='Destination directory')
        parser.add_argument('source_directory', nargs='+', help='Path to source directory to merge into destination directory')
        parser.add_argument('-n', '--dry-run', action='store_true', help='Dry run')
        args = parser.parse_args()
        cls(args).run()

if __name__ == "__main__":
    Tool.main()
