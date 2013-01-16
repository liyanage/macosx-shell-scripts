#!/usr/bin/env python
#
# Converts a set of paths (on stdin, one path per line) into a shell brace expression.
#
# Example:
#
# security
# security/audit_class
# security/audit_control
# security/audit_event
# security/audit_user
# security/audit_warn
# services
# shells
# slpsa.conf
# smb.conf.old
# snmp
# snmp/snmpd.conf
# snmp/snmpd.conf.default
#
# becomes
#
# {smb.conf.old,shells,snmp,snmp/{snmpd.conf.default,snmpd.conf},services,security,security/{audit_control,audit_class,audit_user,audit_warn,audit_event},slpsa.conf}


import re
import sys
import collections

class Node(object):

    def __init__(self, name=None):
        self.name = name
        self.include_self = False
        self.children = {}
    
    def add_path(self, path):
        if not path:
            return
        path = re.sub(r'([^a-zA-Z0-9/_.-])', r'\\\1', path)
        items = path.split('/')
        self.add_path_components(items)

    def add_path_components(self, path_components):
        if not path_components:
            return
        head = path_components[0]
        tail = path_components[1:]
        child = self.children.setdefault(head, Node(head))
        if tail:
            child.add_path_components(tail)
        else:
            child.include_self = True
    
    def shell_brace_expression(self):
        if not self.children:
            return self.name
        
        children = ','.join([child.shell_brace_expression() for child in self.children.values()])
        if len(self.children) > 1:
            children = '{' + children + '}'
        
        if self.name:
            result = ['/'.join([self.name, children])]
            if self.include_self and children:
                result.insert(0, self.name)
            return ','.join(result)
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
