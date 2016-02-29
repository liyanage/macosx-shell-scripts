#!/usr/bin/env python

import sys
import os
import re
import argparse
import logging
import collections
import textwrap


class Tool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        with open(self.args.path) as x: data = x.read()
        items = re.split(r'^\s+\d+\s+\d+\s+xpc_transaction_(begin|end):entry.*$', data, flags=re.MULTILINE)
        while items[0] != 'end' and items[0] != 'begin':
            del(items[0])
        
        item_count = len(items) / 2
        item_count_len = len(str(item_count))
        
        open_transaction_count = 0
        item_index = 0
        stack_frame_re = re.compile(r'\S+`.*')

        stack_counts = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
        
        while items:
            type = items.pop(0)
            details = items.pop(0)
            item_index += 1
            
            if type == 'begin':
                open_transaction_count += 1
            elif type == 'end':
                open_transaction_count -= 1
            else:
                raise 'Invalid type ' + type
            
            stack = '\n'.join(re.findall(stack_frame_re, details))
            stack_counts[type][self.bucket_name_for_stack(stack)][stack] += 1

            if self.args.verbose:
                print '{:>{}} {} {}'.format(item_index, item_count_len, open_transaction_count, '#' * open_transaction_count)

        for type, stack_buckets in stack_counts.items():
            print '{} stacks ------------\n'.format(type)
            for bucket_name, stack_counter in sorted(stack_buckets.items(), lambda a, b: cmp(sum(a[1].values()), sum(b[1].values()))):
                if bucket_name in self.args.groups:
                    if bucket_name in stack_counts['begin'] and bucket_name in stack_counts['end']:
                        if sum(stack_counts['begin'][bucket_name].values()) == sum(stack_counts['end'][bucket_name].values()):
                            continue
                if len(stack_counter) > 1:
                    print 'Group {}\n{}\n'.format(bucket_name, sum(stack_counter.values()))
                for stack, count in sorted(stack_counter.items(), lambda a, b: cmp(a[1], b[1])):
                    print '{}\n{}\n'.format(count, stack)
            
    def bucket_name_for_stack(self, stack):
        for string in self.args.groups:
            if string in stack:
                return string
        return stack

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=textwrap.dedent(r'''
            Summarizes XPC transaction begin/end events from a dtrace script like this:

            -------------------------------------------
            #!/usr/sbin/dtrace -s

            pid$target::xpc_transaction_begin:entry {
                    ustack();
            }

            pid$target::xpc_transaction_end:entry {
                    ustack();
            }
            -------------------------------------------

            Examples:

                find-unbalanced-xpc-transactions.py \
                -g '-[NSXPCConnection _sendInvocation:withProxy:remoteInterface:withErrorHandler:timeout:userInfo:]' \
                -g '-[NSXPCConnection _decodeAndInvokeMessageWithData:]' \
                -g '_xpc_connection_mach_event' \
                /path/to/dtrace-dump.txt

            '''))
        parser.add_argument('path', help='Path to output of dtrace script')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')
        parser.add_argument('-g', '--group', action='append', dest='groups', metavar='STRING', default=[], help='Put distinct stacks containing the given string into the same counting bucket, both for begin and end events. When reporting counts at the end, suppress begin and end stacks whose buckets and counts are both identical. Can be used multiple times.')

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        cls(args).run()


if __name__ == "__main__":
    Tool.main()
