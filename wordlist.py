#!/usr/bin/env python

import random
import copy
import sys

def find_words(node, available, parents=None):
    if parents is None:
        parents = []
    if '_leaf' in node:
        yield ''.join(parents)
    for char in (i for i in set(available) if i in node):
        remaining = copy.copy(available)
        remaining.remove(char)
        for word in find_words(node[char], remaining, parents + [char]):
            yield word

def read_words(filename):
    root = {}
    with open(filename) as f:
        for line in f.readlines():
            line = line.rstrip().lower()
            node = root
            for char in line:
                node = node.setdefault(char, {})
            node['_leaf'] = True
    return root

available_characters = list(sys.argv[1])
length_comparator = lambda x, y: cmp(len(x), len(y))
words = sorted(find_words(read_words('/usr/share/dict/words'), available_characters), length_comparator)
print ' '.join(words)

