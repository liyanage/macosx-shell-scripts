#!/usr/bin/env python3

import sys
import os
import re
import argparse
import logging
from pathlib import Path
import hashlib
import subprocess


class Tool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        for dirpath, dirnames, filenames in os.walk(self.args.path):
            for filename in filenames:
                original_path, duplicate_path = self.original_and_duplicate_for_dirpath_and_name(dirpath, filename)

                if not duplicate_path:
                    continue
                elif not original_path:
                    if self.should_delete_orphaned_duplicate_unconditionally(duplicate_path):
                        print(f'Duplicate without original deleted: {duplicate_path}')
                        duplicate_path.unlink()
                    else:
                        print(f'*** Found duplicate file but not original: {duplicate_path}', file=sys.stderr)
                    continue

                hash_original = self.hash_for_path(original_path)
                hash_duplicate = self.hash_for_path(duplicate_path)
                identical = hash_original == hash_duplicate
#                print(f'Duplicate (identical={identical}) "{duplicate_path}" -> "{original_path}"')

                if identical:
                    self.keep_newer('identical content', original_path, duplicate_path)
                    continue
                else:
                    self.keep_newer('keep newer unconditionally', original_path, duplicate_path)
                    continue
                    # if self.should_keep_newer_unconditionally(original_path, duplicate_path):
                    #     self.keep_newer('consider mtime only', original_path, duplicate_path)
                    #     continue

                print(f'*** Found duplicate with different content: {duplicate_path}', file=sys.stderr)
                cmd = ['diff', '-u', original_path.as_posix(), duplicate_path.as_posix()]
#                subprocess.run(cmd)

            # for filename in dirnames:
            #     head, tail = os.path.splitext(filename)
            #     if trailing_number_re.match(head):
            #         print(dirpath, filename)

        return 1
    
    @classmethod
    def should_keep_newer_unconditionally(cls, original_path, duplicate_path):
        for marker in cls.path_markers():
            if marker in original_path.as_posix():
                return True
        return False
    
    @classmethod
    def should_delete_orphaned_duplicate_unconditionally(cls, duplicate_path):
        suffixes_to_delete_unconditionally = ['.icloud']
        if duplicate_path.suffix in suffixes_to_delete_unconditionally:
            return True
        
        for marker in cls.path_markers():
            if marker in duplicate_path.as_posix():
                return True

    @staticmethod
    def path_markers():
        return '.git/logs/refs', '.git/refs', '.git/worktrees', '.git/index', '.git/ORIG_HEAD'

    @staticmethod
    def keep_newer(label, original_path, duplicate_path):
        mtime_orig = original_path.stat().st_mtime_ns
        mtime_dup = duplicate_path.stat().st_mtime_ns

        if mtime_orig > mtime_dup:
            print(f'Keeping original, deleting duplicate: "{duplicate_path}" ({label})')
            duplicate_path.unlink()
        else:
            print(f'Keeping duplicate: "{duplicate_path}" ({label})')
            duplicate_path.replace(original_path)

    @staticmethod
    def original_and_duplicate_for_dirpath_and_name(dirpath, name):
        potential_duplicate_path = None
        original_path = None

        trailing_number_re = re.compile(r'(.+) \d$')
        head, ext = os.path.splitext(name)
        match = trailing_number_re.match(head)
        if match:
            original_path = Path(dirpath) / Path(match.group(1) + ext)
        
        trailing_icloud_re = re.compile(r'(.+)\.icloud$')
        match = trailing_icloud_re.match(name)
        if match:
            original_path = Path(dirpath) / Path(match.group(1))

        if original_path:            
            potential_duplicate_path = Path(dirpath) / Path(name)
            if not original_path.exists():
                original_path = None

        return original_path, potential_duplicate_path

    @staticmethod
    def hash_for_path(path):
        m = hashlib.md5()
        with open(path.as_posix(), 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                m.update(chunk)
        return m.hexdigest()

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Description')
        parser.add_argument('path', type=Path, help='Path to something')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        return cls(args).run()


if __name__ == "__main__":
    sys.exit(Tool.main())
