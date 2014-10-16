#!/usr/bin/env python

#
# Adjust EXIF dates with exiftool. This will take a batch of JPEG files,
# sort them by name, and then change the EXIF date in each one with an 
# offset of one second per image, ending in the current time.
#
# This requires the "exiftool" utility to be installed: http://www.sno.phy.queensu.ca/~phil/exiftool/
#
# Maintained at https://github.com/liyanage/macosx-shell-scripts
#

import sys
import os
import re
import argparse
import logging
import subprocess
import glob
import datetime

class Tool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        paths = sorted(glob.glob(self.args.pattern))
        paths.reverse()
        now = datetime.datetime.now()
        delta = datetime.timedelta(seconds=1)
        for path in paths:
            now -= delta
            cmd = ['exiftool', '-AllDates={}'.format(now.strftime('%Y:%m:%d %H:%M:%S')), path]
            print ' '.join(cmd)
            subprocess.check_call(cmd)

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Adjust EXIF dates with exiftool.')
        parser.add_argument('pattern', help='Glob pattern for image files to change')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        cls(args).run()


if __name__ == "__main__":
    Tool.main()
