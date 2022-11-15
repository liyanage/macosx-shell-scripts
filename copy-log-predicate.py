#!/usr/bin/env python3

import sys
import os
import re
import argparse
import subprocess


class Tool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        with open(os.path.expanduser('~/.logrc')) as x: logrc = x.read()

        sections = re.split(r'^(\w+):', logrc, flags=re.MULTILINE)
        del(sections[0])
        while sections:
            key, value = sections.pop(0), sections.pop(0)
            if key != 'predicate':
                continue

            aliases = re.split(r'^\s+(\w+)\s*$', value, flags=re.MULTILINE)
            del(aliases[0])

            predicates = {}

            while aliases:
                key, value = aliases.pop(0), aliases.pop(0)
                if key not in self.args.predicate_aliases:
                    continue
                assert key not in predicates
                concatenated = re.sub(r'\s*$\s*', '', value, flags=re.MULTILINE)
                concatenated = concatenated.replace("''", " ")
                concatenated = concatenated.strip("'")
                predicates[key] = concatenated

            if len(predicates) != len(self.args.predicate_aliases):
                print(self.args.predicate_aliases)
                missing_keys = set(self.args.predicate_aliases) - set(predicates.keys())
                raise Exception(f'Unable to find predicate for key(s) {", ".join(missing_keys)}')

            predicate = None
            if len(predicates) > 1:
                predicate = ' OR '.join([f'({p})' for p in predicates.values()])
            else:
                assert len(predicates) == 1
                predicate = list(predicates.values())[0]
            
            predicate = f"'{predicate}'"

            print(predicate)
            subprocess.run(['pbcopy'], input=predicate, text=True)

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Copy ~/.logrc predicates to clipboard')
        parser.add_argument('predicate_aliases', nargs='+', help='Aliases for the predicate to be used. If multiple are given, combine them with logical OR.')
        return cls(parser.parse_args()).run()

if __name__ == "__main__":
    sys.exit(Tool.main())








