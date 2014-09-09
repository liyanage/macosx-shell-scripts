#!/usr/bin/env python
#
# Print histogram of frequency of input lines
#
# Maintained at http://github.com/liyanage/macosx-shell-scripts
#

import sys
import os
import re
import argparse
import logging
import fileinput
import subprocess
import collections


class HistogramCounter(object):
    
    def __init__(self, item_regex=None, cost_regex=None, cost_coefficient=None):
        self.item_regex = item_regex
        self.cost_regex = cost_regex
        self.cost_coefficient = cost_coefficient
        self.total_count = 0
        self.total_cost = 0
        self.setup_data()
    
    def setup_data(self):

        class CostInfo(object):

            def __init__(self):
                self.count = 0
                self.total_cost = 0
            
            def update(self, cost=1):
                self.count += 1
                self.total_cost += cost
        
        self.data = collections.defaultdict(CostInfo)

    def update(self, iterable):
        for line in iterable:
            item_identifier = line
            if self.item_regex:
                values = self.item_regex.findall(line)
                if not values:
                    continue
                item_identifier = values[0]
            cost = 1.0
            if self.cost_regex:
                values = self.cost_regex.findall(line)
                if not values:
                    print >> sys.stderr, 'Cost regex given, but input line does not match: "{}"'.format(line)
                    sys.exit(1)
                cost = float(values[0])
            if self.cost_coefficient:
                cost *= self.cost_coefficient
            self.data[item_identifier].update(cost)
            self.total_count += 1
            self.total_cost += cost

    def max_len_total_cost(self):
        return max([len(str(i.total_cost)) for i in self.data.values()])

    def sorted_items(self):
        return sorted(self.data.items(), cmp=lambda a, b: cmp(b[1].total_cost, a[1].total_cost))

    def print_histogram(self):
        with open('/dev/tty') as tty:
            lines, columns = [int(x) for x in subprocess.check_output(['stty', 'size'], stdin=tty).split()]

        sorted_items = self.sorted_items()

        max_len_total_cost = self.max_len_total_cost()
        item_width = columns / 2
        max_bar_length = item_width - (13 + max_len_total_cost)
        scale = float(max_bar_length) / sorted_items[0][1].total_cost

        for item, cost_info in sorted_items:
            bar_length = int(scale * cost_info.total_cost)
            percentage = int(cost_info.total_cost * 100 / self.total_cost)
            print '{:{width}}  {:4} {:{width_cost}.0f} {:>3}% {}'.format(item.strip()[:item_width], cost_info.count, cost_info.total_cost, percentage, '*' * bar_length, width=item_width, width_cost=max_len_total_cost)


class Tool(object):

    def __init__(self, args):
        self.args = args
        self.counter = HistogramCounter(self.args.item_regex, self.args.cost_regex, self.args.cost_scale)

    def run(self):
        for input_file in self.args.input_files:
            self.counter.update(input_file)
        print '{} total item(s), {:.0f} total cost'.format(self.counter.total_count, self.counter.total_cost)
        if not self.counter.total_count:
            return
        self.counter.print_histogram()

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Print histogram of frequency of input lines')
        parser.add_argument('input_files', nargs='*', type=argparse.FileType('r'), default=[sys.stdin], help='Input file paths, defaults to stdin')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')
        parser.add_argument('-i', '--item-regex', type=re.compile, help='Optional regular expression to select part of each input line for counting purposes')
        parser.add_argument('-c', '--cost-regex', type=re.compile, help='Optional regular expression to select a cost value in each input line')
        parser.add_argument('-s', '--cost-scale', type=float, help='Optional cost scale coefficient')

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        cls(args).run()


if __name__ == "__main__":
    Tool.main()




