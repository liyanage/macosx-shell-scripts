#!/usr/bin/env python

#
# Detect and fix symlinks (in specific locations only) that were corrupted
# by Dropbox and replaced with their target files
#
# Maintained at https://github.com/liyanage/macosx-shell-scripts
#


import sys
import os
import re
import argparse
import logging
import difflib
import subprocess

class Tool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        for dirpath, dirnames, filenames in os.walk(os.path.expanduser('~/bin')):
            del dirnames[:]
            bin_files = set([f for f in filenames if not os.path.islink(os.path.join(dirpath, f))])

        identical_files_cmds = []

        for dirpath, dirnames, filenames in os.walk(os.path.expanduser('~/git')):
            for filename in filenames:
                if filename not in bin_files:
                    continue

                bin_path = os.path.join(os.path.expanduser('~/bin'), filename)
                with open(bin_path) as x: bin_content = x.readlines()

                git_path = os.path.join(dirpath, filename)
                if not os.path.exists(git_path):
                    continue
                with open(git_path) as x: git_content = x.readlines()

                git_relpath = os.path.relpath(git_path, os.path.dirname(bin_path))
                ln_cmd = 'ln -fs {} {}'.format(git_relpath, bin_path)

                if bin_content == git_content:
                    identical_files_cmds.append(ln_cmd)
                else:
                    if '#!' in bin_content[0]:
                        print 'File differs, please resolve and re-run'
                        # for line in difflib.unified_diff(bin_content, git_content, fromfile=bin_path, tofile=git_path):
                        #     print line,
                        self.run_bbedit(bin_path, git_path)                        
                        print '*** Keep ~/bin version: cp {} {}'.format(bin_path, git_path)
                        print '*** Keep other version: {}'.format(ln_cmd)
                    else:
                        print 'Binary file differs, please resolve and re-run: {} {}'.format(bin_path, git_path)

                    print                

        if identical_files_cmds:
            print 'Identical files:'
            for cmd in identical_files_cmds:
                print cmd

    @staticmethod
    def run_bbedit(path1, path2):
        cmd = ['osascript', '-e', 'tell application "BBEdit" to compare "{}" against "{}"'.format(path1, path2)]
        subprocess.call(cmd, stdout=subprocess.PIPE)
        subprocess.call(['osascript', '-e', 'tell application "BBEdit" to activate'], stdout=subprocess.PIPE)

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Detect and fix symlinks that were corrupted by Dropbox')
        args = parser.parse_args()
        cls(args).run()


if __name__ == "__main__":
    Tool.main()
