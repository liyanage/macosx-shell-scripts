#!/usr/bin/env python
#
# Print histogram of frequency of input lines
#
# Maintained at http://github.com/liyanage/macosx-shell-scripts
#

import sys
import os
import re
import math
import argparse
import logging
import fileinput
import subprocess
import collections



class BaseCounter(object):
    
    def __init__(self, item_regex=None, cost_regex=None, cost_coefficient=None, expand_tabs=None):
        self.item_regex = item_regex
        self.cost_regex = cost_regex
        self.cost_coefficient = cost_coefficient
        self.expand_tabs = expand_tabs
        self.total_count = 0
        self.total_cost = 0
        self.setup_data()
    
    def setup_data(self):
        pass

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
                    continue
                cost = float(values[0])
            if self.cost_coefficient:
                cost *= self.cost_coefficient
            
            self.total_count += 1
            self.total_cost += cost
            self.update_for_item_and_cost(item_identifier, cost)

    def update_for_item_and_cost(self, item_identifier, cost):
        pass

    def print_histogram(self):
        pass

    @classmethod    
    def terminal_width(cls):
        with open('/dev/tty') as tty:
            lines, columns = [int(x) for x in subprocess.check_output(['stty', 'size'], stdin=tty).split()]
            return columns


class DefaultCounter(BaseCounter):
        
    def setup_data(self):

        class CostInfo(object):

            def __init__(self):
                self.count = 0
                self.total_cost = 0
            
            def update(self, cost=1):
                self.count += 1
                self.total_cost += cost
        
        self.data = collections.defaultdict(CostInfo)

    def update_for_item_and_cost(self, item_identifier, cost):
        self.data[item_identifier].update(cost)

    def max_len_total_cost(self):
        return max([len(str(i.total_cost)) for i in self.data.values()])

    def sorted_items(self):
        return sorted(self.data.items(), cmp=lambda a, b: cmp(b[1].total_cost, a[1].total_cost))

    def print_histogram(self):
        terminal_width = self.terminal_width()

        sorted_items = self.sorted_items()

        max_len_total_cost = self.max_len_total_cost()
        item_width = terminal_width / 2
        max_bar_length = item_width - (13 + max_len_total_cost)
        scale = float(max_bar_length) / sorted_items[0][1].total_cost

        for item, cost_info in sorted_items:
            if self.expand_tabs:
                item = item.expandtabs(self.expand_tabs)
            bar_length = int(scale * cost_info.total_cost)
            percentage = int(cost_info.total_cost * 100 / self.total_cost)
            print '{:{width}}  {:4} {:{width_cost}.0f} {:>3}% {}'.format(item.strip()[:item_width], cost_info.count, cost_info.total_cost, percentage, '*' * bar_length, width=item_width, width_cost=max_len_total_cost)


class BucketCounter(BaseCounter):

    def setup_data(self):
        
        class BucketCostInfo(object):

            def __init__(self):
                self.count = 0
                self.total_cost = 0
                self.item_counter = collections.Counter()
            
            def update(self, cost, item):
                self.count += 1
                self.total_cost += cost
                self.item_counter.update([item])

        self.zero_bucket = BucketCostInfo()    
        self.data = collections.defaultdict(BucketCostInfo)

    def update_for_item_and_cost(self, item_identifier, cost):
        bucket_id = int(math.log(cost, 2))
        self.data[bucket_id].update(cost, item_identifier)

    def sorted_buckets(self):
        return sorted(self.data.items(), cmp=lambda a, b: cmp(b[0], a[0]))

    def print_histogram(self):
        sorted_buckets = self.sorted_buckets()
        min_bucket, max_bucket = sorted_buckets[-1][0], sorted_buckets[0][0]
        max_count = max(self.data.values(), key=lambda x: x.count).count

        terminal_width = self.terminal_width()
        item_width = terminal_width / 2
        max_bar_length = item_width - (13 + 0)
        scale = float(max_bar_length) / max_count

        for i in range(min_bucket, max_bucket + 1):
            bucket = self.data.get(i, self.zero_bucket)
            bar_length = int(scale * bucket.count)
            percentage = int(bucket.count * 100 / self.total_count)
            print '{:{width}}  {:5}  {:>3}% {}'.format(2 ** i, bucket.count, percentage, '*' * bar_length, width=item_width)

        for i in range(min_bucket, max_bucket + 1):
            bucket = self.data.get(i, self.zero_bucket)
            if not bucket.count:
                continue

            bar_length = int(scale * bucket.count)
            percentage = int(bucket.count * 100 / self.total_count)
            print '{}'.format(2 ** i)
            print '{:>3}% {}'.format(percentage, '*' * bar_length)
            for item, count in bucket.item_counter.most_common(10):
                print '{:4} {}'.format(count, item)
            print


class Tool(object):

    def __init__(self, args):
        self.args = args
        counter_class = BucketCounter if self.args.cost_distribution else DefaultCounter
        self.counter = counter_class(self.args.item_regex, self.args.cost_regex, self.args.cost_scale, self.args.expand_tabs)

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
        parser.add_argument('-t', '--expand-tabs', type=int, default=4, help='Optional tab expansion column width. A value of 0 means do not expand tabs. Default is 4.')
        parser.add_argument('-d', '--cost-distribution', action='store_true', help='Plot and order by the distribution of the cost values')

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        cls(args).run()


if __name__ == "__main__":
    Tool.main()




