#!/usr/bin/env python

# Maintained at https://github.com/liyanage/macosx-shell-scripts/
#

import sys
import os
import re
import argparse
import logging
import Foundation
import subprocess

class Tool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        if self.args.action == 'toggle':
            self.toggle()
        elif self.args.action == 'show':
            self.show()
        elif self.args.action == 'hide':
            self.hide()
        elif self.args.action == 'auto':
            self.auto()
    
    def show(self):
        self.set_hidden_state(False)

    def hide(self):
        self.set_hidden_state(True)

    def toggle(self):
        self.set_hidden_state(not self.is_currently_hidden())
    
    def auto(self):
        try:
            self.hide()
            raw_input('Desktop hidden, hit Return to unhide:\n')
        except BaseException:
            pass
        finally:
            self.show()

    def set_hidden_state(self, new_state):
        if new_state == self.is_currently_hidden():
            return
        
        if new_state:
            cmd = 'defaults write com.apple.finder CreateDesktop -bool false'.split()
        else:
            cmd = 'defaults delete com.apple.finder CreateDesktop'.split()
            
        subprocess.check_call(cmd)
        subprocess.check_call('killall Finder'.split())
        
    def is_currently_hidden(self):
        finder_settings = Foundation.NSUserDefaults.standardUserDefaults().persistentDomainForName_("com.apple.finder")
        if 'CreateDesktop' in finder_settings:
            return not finder_settings['CreateDesktop']
        return False

    @classmethod
    def main(cls):
        action_default = 'auto' if sys.stdout.isatty() else 'toggle'
        parser = argparse.ArgumentParser(description='Hide/show Desktop contents, for presentations / screen recordings / screenshots')
        parser.add_argument('action', nargs='?', default=action_default, choices=['hide', 'show', 'toggle', 'auto'], help='Action to perform')

        args = parser.parse_args()
        cls(args).run()


if __name__ == "__main__":
    Tool.main()
