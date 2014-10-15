#!/usr/bin/env python
#
# Dropbox conflict helper. To be run from within a BBEdit shell worksheet
#
# Written by Marc Liyanage
#
# https://github.com/liyanage/macosx-shell-scripts
#

import re
import os
import sys
import hashlib
import datetime
import argparse
import subprocess


class DuplicateFile(object):

    def __init__(self, path):
        assert os.path.exists(path), 'Invalid path: {}'.format(path)
        self.path = path
        self.cached_hexdigest = None
        self.cached_last_modified_timestamp = None
    
    def hexdigest(self):
        if not self.cached_hexdigest:
            hash = hashlib.new('md5')
            with open(self.path) as f:
                hash.update(f.read())
            self.cached_hexdigest = hash.hexdigest()
        return self.cached_hexdigest
    
    def last_modified_timestamp(self):
        if not self.cached_last_modified_timestamp:
            self.cached_last_modified_timestamp = datetime.datetime.fromtimestamp(os.stat(self.path).st_mtime)
        return self.cached_last_modified_timestamp
    
    def is_symlink(self):
        return os.path.islink(self.path)


class DuplicateSet(object):

    def __init__(self, original_path):
        self.original_file = DuplicateFile(original_path)
        self.duplicate_files = []

    def add_duplicate_path(self, path):
        self.duplicate_files.append(DuplicateFile(path))
    
    def all_duplicates_are_identical(self):
        if self.duplicates_contain_symlinks():
            return False

        hashes = set()
        for file in self.all_files():
            hashes.add(file.hexdigest())
        return len(hashes) == 1

    def duplicates_contain_symlinks(self):
        for file in self.all_files():
            if file.is_symlink():
                return True
        return False
    
    def all_files(self):
        return [self.original_file] + self.duplicate_files
    
    def all_files_ordered_by_date(self):
        return sorted(self.all_files(), cmp=lambda a, b: cmp(b.last_modified_timestamp(), a.last_modified_timestamp()))

    def summary(self, keep_newest=False):
        summary = ''
        for duplicate_file in self.all_files_ordered_by_date():
            summary += '# ' + subprocess.check_output(['ls', '-l', duplicate_file.path])

        if self.all_duplicates_are_identical():
            summary += '# All duplicates identical\n'
        if self.duplicates_contain_symlinks():
            summary += '# Duplicates contain symlinks\n'
        return summary

    def delete_all_duplicates_worksheet_content(self):
        worksheet_content = ''
        for duplicate_file in self.duplicate_files:
            worksheet_content += 'rm "{}"\n'.format(duplicate_file.path, self.original_file.path)
        return worksheet_content

    def worksheet_content(self, keep_newest=False):
        if self.all_duplicates_are_identical():
            return self.delete_all_duplicates_worksheet_content()

        worksheet_content = ''
        if keep_newest:
            all_files = self.all_files_ordered_by_date()
            newest_file = all_files[0]
            if self.original_file == newest_file:
                return self.delete_all_duplicates_worksheet_content()
            
            original_path = self.original_file.path
            for file in all_files[1:]:
                worksheet_content += '# diff -u "{}" "{}"\n'.format(newest_file.path, file.path)
                if file.path != original_path:
                    worksheet_content += 'rm "{}"\n'.format(file.path)
            worksheet_content += 'mv "{}" "{}"\n'.format(newest_file.path, original_path)
            return worksheet_content

        for duplicate_file in self.duplicate_files:
            if not self.all_duplicates_are_identical():
                worksheet_content += 'diff -u "{}" "{}"\n'.format(self.original_file.path, duplicate_file.path)
                worksheet_content += 'mv "{}" "{}"\n'.format(duplicate_file.path, self.original_file.path)
            worksheet_content += 'rm "{}"\n'.format(duplicate_file.path)
        return worksheet_content
    
    def __str__(self):
        return '<Duplicate {}>'.format(self.original_file.path)


class Tool(object):

    def __init__(self, args):
        self.args = args
        self.dropbox_path = os.path.expanduser(args.dropbox_path)
        assert os.path.exists(self.dropbox_path), 'Invalid Dropbox path {}'.format(dropbox_path)
        self.duplicate_sets = []
        self.duplicate_set_map = {}
        self.running_from_worksheet = 'BBEDIT_CLIENT_INTERACTIVE' in os.environ
    
    def run(self):
        self.gather_duplicates()
        self.process_duplicates()
    
    def gather_duplicates(self):
        limit = 0
        count = 0
        for root, dirs, files in os.walk(self.dropbox_path):
            if '.dropbox.cache' in dirs:
                del(dirs[dirs.index('.dropbox.cache')])

            for file in files:
                match = re.match(r'^(.*?) \([^\(]+ conflicted copy [^)]+\)(.*)$', file)
                if not match:
                    continue

                count += 1
                if limit and count > limit:
                    return

                original_name = match.group(1)
                extension = match.group(2)
                if extension:
                    original_name += extension

                full_path = os.path.join(root, original_name)
#                print file
                assert os.path.exists(full_path), 'Invalid path: {}'.format(full_path)
                duplicate_set = self.duplicate_set_for_original_path(full_path)
                duplicate_set.add_duplicate_path(os.path.join(root, file))

    def process_duplicates(self):
        if not self.duplicate_sets:
            print 'No conflicted files found'
            return
            
        if not self.running_from_worksheet:
            bbedit = subprocess.Popen(['bbedit', '-s'], stdin=subprocess.PIPE)
            
        for duplicate_set in self.duplicate_sets:
#             if duplicate_set.all_duplicates_are_identical():
#                 continue
            text = '# {}\n'.format(duplicate_set)
            text += duplicate_set.summary(keep_newest=self.args.keep_newest)
            text += duplicate_set.worksheet_content(keep_newest=self.args.keep_newest)
            text += '\n'
            if self.running_from_worksheet:
                sys.stdout.write(text)
            else:
                bbedit.stdin.write(text)

    def duplicate_set_for_original_path(self, path):
        duplicate_set = self.duplicate_set_map.get(path, None)
        if not duplicate_set:
            duplicate_set = DuplicateSet(path)
            self.duplicate_sets.append(duplicate_set)
            self.duplicate_set_map[path] = duplicate_set
        return duplicate_set

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Helper to process Dropbox conflict duplicates')
        parser.add_argument('dropbox_path', help='Path to Drobox folder')
        parser.add_argument('-n', '--keep-newest', action='store_true', default=True, help='Default to keeping the newest duplicate of a file')

        args = parser.parse_args()
        cls(args).run()


if __name__ == '__main__':
    Tool.main()