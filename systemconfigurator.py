#!/usr/bin/env python3


import sys
import os
import re
import shutil
import argparse
import subprocess
import plistlib
import logging
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional, Any, NoReturn


class Tool(object):

    def __init__(self, args):
        self.args = args
        self.cached_icloud_account_info = None

    def run(self):
        self.check_icloud_account()
        self.icloud_service_enabled(identifier='MOBILE_DOCUMENTS', label='Mobile Documents')
        self.icloud_service_enabled(identifier='CLOUDDESKTOP', label='iCloud Drive > Desktop')

        self.copy_to_directory(source='~/Documents/Fonts/LucasFonts/OpenType/TheSansMonoCd OT/TheSansMonoCd-W5Regular.otf', destination_directory='~/Library/Fonts')
        self.copy_to_directory(source='~/Documents/Fonts/LucasFonts/OpenType/TheSansMonoCd OT/TheSansMonoCd-W5RegularItal.otf', destination_directory='~/Library/Fonts')
        self.copy_to_directory(source='~/Documents/Fonts/LucasFonts/OpenType/TheSansMonoCd OT/TheSansMonoCd-W7Bold.otf', destination_directory='~/Library/Fonts')
        self.copy_to_directory(source='~/Documents/Fonts/LucasFonts/OpenType/TheSansMonoCd OT/TheSansMonoCd-W7BoldItalic.otf', destination_directory='~/Library/Fonts')

        self.check_terminal_window_settings(name='Marc’s Settings', source='~/Documents/Theme Settings/Terminal/Marc’s Settings.terminal')

        self.symlink(at="~/bin", destination="Documents/bin")
        self.symlink(at="~/git", destination="Documents/git")
        self.symlink(at="~/.dotfiles", destination="git/dotfiles")
        self.symlink(at="~/.oh-my-zsh", destination=".dotfiles/.oh-my-zsh")
        self.symlink(at="~/.config", destination=".dotfiles/.config")
        self.symlink(at="~/.zshrc", destination=".dotfiles/.zshrc")
        self.symlink(at="~/.vimrc", destination=".dotfiles/.vimrc")
        self.symlink(at="~/.logrc", destination=".dotfiles/.logrc")
        self.symlink(at="~/.jupyter", destination=".dotfiles/.jupyter")
        self.symlink(at="~/.gitconfig", destination=".dotfiles/.gitconfig")
        self.symlink(at="~/.gitignore.global", destination=".dotfiles/.gitignore.global")
        self.symlink(at="~/.cplstoreconfig", destination=".dotfiles/.cplstoreconfig")

        self.login_item('Activity Monitor', '/System/Applications/Utilities/Activity Monitor.app')

        # Most user defaults tracked down with:
        # log stream --debug --predicate 'subsystem = "com.apple.defaults" and eventMessage contains "setting {"'
        self.user_defaults('com.apple.Dock', {'autohide': True, 'orientation': 'left'}, 'Dock')
        self.user_defaults('com.apple.ActivityMonitor', {'IconType': 6}, 'Activity Monitor')
        self.user_defaults('-g', {'InitialKeyRepeat': 15, 'KeyRepeat': 2})
        # https://www.macworld.com/article/178496/crashreport.html
        # https://www.defaults-write.com/os-x-make-crash-reporter-appear-as-a-notification/
        self.user_defaults('com.apple.CrashReporter', {'DialogType': 'developer', 'UseRegularActivationPolicy': True, 'UseUNC': True})

        # This one doesn't work because this domain is not writable via command line tools.
        self.user_defaults('com.apple.universalaccess', {'com.apple.custommenu.apps': ['com.apple.mail']})
        self.user_defaults('com.apple.mail', {
            'ConversationViewSortDescending': True,
            'SuppressDeliveryFailure': True,
            'AutoReplyFormat': True,
            'NSFixedPitchFont': 'TheSansMonoCd-W5Regular',
            'AlertForNonmatchingDomains': True,
            'DomainForMatching': ['@apple.com', '@group.apple.com'],
            'NSFixedPitchFontSize': 12,
            'NumberOfSnippetLines': 1,
            'MailUserNotificationScope': 2,
            'CustomHeaders': ['List-Id', 'X-Member-Count'],
            'NSUserKeyEquivalents': {'Mark All Messages as Read': '^r'}
        })

        self.user_defaults('com.apple.Terminal', {'NewWindowWorkingDirectoryBehavior': 2})

        self.app_store_app('BetterSnapTool', '417375580')
        self.user_defaults('com.hegenberg.BetterSnapTool', {
            'shiftMove': True,
            'cmdMove': True,
            'shiftResize': True,
            'optResize': True,
            'snapBottomLeft': False,
            'snapBottomRight': False,
            'snapLeft': False,
            'snapRight': False,
            'snapTop': False,
            'snapTopLeft': False,
            'snapTopRight': False,
        })

        self.app_store_app('Paste', '967805235')
        self.app_store_app('Step Two', '1448916662')
        self.app_store_app('Slack', '803453959')
        self.app_store_app('1Blocker', '1365531024')

        return 0

    def app_store_app(self, name: str, identifier: str):
        cmd = '/Users/liyanage/bin/mas', 'account'
        result = subprocess.run(cmd, capture_output=True, text=True)
        if '@' not in result.stdout:
            self.fatal_exit(f'Please sign in to the Mac App Store and ensure the "mas" command line tool is installed: https://github.com/mas-cli/mas')
        cmd = '/Users/liyanage/bin/mas', 'list'
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.fatal_exit(f'"mas list" returned non-zero exit code: {result.stderr}')

        installed_apps = re.findall(r'^(\d+)\s+(.+?)\s+\((.+)\)$', result.stdout, flags=re.MULTILINE)
        installed_apps = {x[0]: x[1] for x in installed_apps}
        if identifier in installed_apps and installed_apps[identifier] == name:
            return
        print(f'Installing "{name}" from Mac App Store')
        cmd = '/Users/liyanage/bin/mas', 'install', str(identifier)
        result = subprocess.run(cmd, text=True, capture_output=True)

    def login_item(self, name, path):
        cmd = 'osascript', '-e', 'tell application "System Events" to login items'
        result = subprocess.run(cmd, text=True, capture_output=True)
        current_items = re.findall(r'login item (.+?)[,\n]', result.stdout)
        if name in current_items:
            return

        path = Path(path)
        if not path.exists():
            self.fatal_exit(f'Path for login item does not exist: {path.as_posix()}')

        cmd = 'osascript', '-e', f'tell application "System Events" to make login item at end with properties {{path:"{path.as_posix()}", hidden:false}}'
        subprocess.run(cmd)

    def user_defaults(self, domain: str, pairs: Dict[str, Any], process_to_kill: str=None):

        def defaults_value_arguments_for_value(key, value):
            if isinstance(value, bool):
                return ['-bool', 'YES' if value else 'NO']
            elif isinstance(value, int):
                return ['-int', str(value)]
            elif isinstance(value, str):
                return [value]
            else:
                self.fatal_exit(f'Unknown data type "{type(value)}" for defaults domain/key "{domain}/{key}"')

        def run_user_default_command(cmd):
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f'Unable to execute command "{" ".join(cmd)}", please perform the equivalent UI action manually. Error: "{result.stderr.strip()}"')

        current_defaults = self.user_defaults_for_domain(domain)
        did_write = False
        for key, value in pairs.items():
            current_value = current_defaults.get(key)
            cmd = ['defaults', 'write', domain, key]
            if isinstance(value, dict):
                for key2, value2 in value.items():
                    if isinstance(current_value, dict) and key2 in current_value and current_value[key2] == value2:
                        continue
                    did_write = True
                    cmd2 = cmd + ['-dict-add', key2] + defaults_value_arguments_for_value(f'{key}.{key2}', value2)
                    run_user_default_command(cmd2)
            elif isinstance(value, list):
                for value2 in value:
                    if isinstance(current_value, list) and value2 in current_value:
                        continue
                    did_write = True
                    cmd2 = cmd + ['-array-add'] + defaults_value_arguments_for_value(key, value2)
                    run_user_default_command(cmd2)
            else:
                if current_value is not None and current_value == value:
                    continue
                did_write = True
                cmd += defaults_value_arguments_for_value(key, value)
                run_user_default_command(cmd)
        if did_write and process_to_kill:
            cmd = 'pkill', '-x', process_to_kill
            subprocess.run(cmd)

    def check_terminal_window_settings(self, name, source):
        source = self.path_for_source(source)
        defaults = self.user_defaults_for_domain('com.apple.Terminal')
        window_settings = defaults['Window Settings']
        logging.debug(window_settings.keys())
        if name not in window_settings:
            self.fatal_exit(f'Terminal config "{name}" not found in Terminal preferences, please import config "{source}"')
        keys = 'Startup Window Settings', 'Default Window Settings'
        for key in keys:
            default_window_settings = defaults.get(key)
            if default_window_settings != name:
                cmd = 'defaults', 'write', 'com.apple.Terminal', key, name
                subprocess.run(cmd)

    def user_defaults_for_domain(self, domain):
#        cmd = 'defaults', 'export', domain, '-'
        cmd = f'defaults export {domain} - | plutil -convert binary1 -o - -'
        return self.plist_for_command(cmd, shell=True)

    def path_for_source(self, path_string):
        path = Path(path_string).expanduser()
        if not path.exists():
            self.fatal_exit(f'"{path}" does not exist')
        return path

    def symlink(self, at, destination):
        at = Path(at).expanduser()
        destination = Path(destination).expanduser()

        if at.exists():
            if at.is_symlink():
                current_destination = os.readlink(at)
                if current_destination == destination.as_posix():
                    return
                self.fatal_exit(f'"{at}" is a symlink but points to "{current_destination}" instead of "{destination}"')
            self.fatal_exit(f'"{at}" exists but is not a symlink')
        at.symlink_to(destination)

    def copy_to_directory(self, source, destination_directory, create_destination=False):
        source = self.path_for_source(source)

        destination_dir = Path(destination_directory).expanduser()
        if destination_dir.exists():
            if not destination_dir.is_dir():
                self.fatal_exit(f'"{destination_dir}" exists but is not a directory')
        else:
            if create_destination:
                destination_dir.mkdir(parents=True)
            else:
                self.fatal_exit(f'"{destination_dir}" directory does not exist and create_destination is not set')

        destination = destination_dir / source.name

        if destination.exists():
            if not destination.is_file():
                self.fatal_exit(f'"{destination}" exists but is not a file')
            if destination.stat().st_size == source.stat().st_size:
                return
            else:
                self.fatal_exit(f'"{destination}" exists but has different length from "{source}"')

        shutil.copy(source, destination)

    def icloud_service_enabled(self, *, identifier, label):
        is_enabled = True
        for service in self.icloud_account_info()['Services']:
            name = service['Name']
            if name != identifier:
                continue
            logging.debug(service)
            enabled = service.get('Enabled')
            if enabled:
                is_enabled = bool(enabled)
            status = service.get('status')
            if status:
                is_enabled = status == 'active'
        if not is_enabled:
            self.fatal_exit(f'Please enable iCloud service {label}')

    def check_icloud_account(self):
        ai = self.icloud_account_info()
        logging.debug(ai)
    
    def plist_for_command(self, cmd, shell=False):
        logging.debug(cmd)
        result = subprocess.run(cmd, capture_output=True, shell=shell)
        return plistlib.loads(result.stdout)
    
    def icloud_account_info(self):
        if not self.cached_icloud_account_info:
            ai = self.user_defaults_for_domain('MobileMeAccounts')
            if 'Accounts' not in ai:
                self.fatal_exit('Please sign into iCloud')
            self.cached_icloud_account_info = ai['Accounts'][0]
        return self.cached_icloud_account_info
    
    def fatal_exit(self, msg):
        print(msg, file=sys.stderr)
        sys.exit(1)

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Description')
        # parser.add_argument('path', type=Path, help='Path to something')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        return cls(args).run()


if __name__ == "__main__":
    sys.exit(Tool.main())
