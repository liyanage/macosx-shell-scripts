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
import struct


class Tool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        print(self.jpeg_length_of_data_after_end_of_image_marker(self.args.path))

    @classmethod
    def jpeg_length_of_data_after_end_of_image_marker(cls, path):
        with open(path, 'rb') as f:
            ba = f.read()
            position = 0
            total_length = len(ba)
            while position < total_length:
                #print position
                tag_bytes = ba[position:position + 2]
                position += 2
                #print 'tag ' + ''.join('{:02x}'.format(ord(b)) for b in tag_bytes)
                if tag_bytes == b'\xff\xd8': # start-of-image
                    continue
                length, = struct.unpack('>H', ba[position:position + 2])
                position += length
                #print 'length {}'.format(length)
                if tag_bytes == b'\xff\xda': # start-of-sample (start of image data)
                    eoi_position = ba.find(b'\xff\xd9', position)
                    #print eoi_position
                    return total_length - (eoi_position + 2)
        return 0

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Description')
        parser.add_argument('path', help='Path to something')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        return cls(args).run()


if __name__ == "__main__":
    sys.exit(Tool.main())
