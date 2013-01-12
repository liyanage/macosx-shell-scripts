#!/usr/bin/env python

import re
import sys
import collections

class Node(object):

    def __init__(self, name=None):
        self.name = name
        self.children = {}
    
    def add_path(self, path):
        if not path:
            return
        items = path.split('/')
        self.add_path_components(items)

    def add_path_components(self, path_components):
        if not path_components:
            return
        head = path_components[0]
        child = self.children.setdefault(head, Node(head))
        child.add_path_components(path_components[1:])
    
    def shell_brace_expression(self):
        if not self.children:
            return self.name
        
        children = ','.join([child.shell_brace_expression() for child in self.children.values()])
        if len(self.children) > 1:
            children = '{' + children + '}'
        
        if self.name:
            return '/'.join([self.name, children])
        else:
            return children

    @classmethod
    def shell_brace_expression_for_paths(cls, paths):
        root = cls()
        for path in paths:
            root.add_path(path)
        return root.shell_brace_expression()

paths = [line.rstrip() for line in sys.stdin.readlines()]
print Node.shell_brace_expression_for_paths(paths)
