#!/usr/bin/env python

#
# Library and tool for some OS X DMG file operation, using hdiutil
#
# Maintained at https://github.com/liyanage/macosx-shell-scripts
#

import os
import re
import sys
import glob
import shutil
import logging
import argparse
import datetime
import plistlib
import tempfile
import subprocess
import contextlib
import collections

class DiskImage(object):

    def __init__(self, dmg_url_or_path):
        self.dmg_url_or_path = dmg_url_or_path
        self.is_remote = bool(re.match(r'^https?://', dmg_url_or_path))
        self.converted_mount_path = None
        self.mount_data = None
        self.info_data = None
    
    def __del__(self):
        if self.converted_mount_path:
            logging.debug('Cleaning up "{}"'.format(self.converted_mount_path))
            os.unlink(self.converted_mount_path)
    
    def info(self):
        if not self.info_data:
            cmd = ['imageinfo', '-plist', self.dmg_url_or_path]
            self.info_data = self.run_hdiutil_plist_command(cmd)
        return self.info_data
    
    def has_license_agreement(self):
        return self.info()['Properties']['Software License Agreement']
    
    def mount(self):
        mount_path = self.dmg_url_or_path
        if self.has_license_agreement():
            print >> sys.stderr, 'Stripping license agreement...'
            tempfile_path = tempfile.mktemp(dir=os.environ['TMPDIR'])
            cmd = ['convert', self.dmg_url_or_path, '-plist', '-format', 'UDTO', '-o', tempfile_path]
            convert_data = self.run_hdiutil_plist_command(cmd)
            self.converted_mount_path, = convert_data
            mount_path = self.converted_mount_path

        cmd = ['mount', '-plist', mount_path]
        self.mount_data = self.run_hdiutil_plist_command(cmd)

    def mount_point(self):
        mount_points = []
        for item in self.mount_data['system-entities']:
            if 'mount-point' not in item:
                continue
            path = item['mount-point']
            mount_points.append(path)
        return mount_points[0] if mount_points else None
    
    def unmount(self):
        cmd = ['unmount', self.mount_point()]
        status, stdout, stderr = self.run_hdiutil_command(cmd)
    
    def run_hdiutil_command(self, cmd, input=None):
        cmd = ['hdiutil'] + cmd
        stdin = subprocess.PIPE if input else None
        process = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stdin=stdin)
        stdoutdata, stderrdata = process.communicate()
        logging.debug('ran cmd "{}": returncode={}, stdout={}, stderr={}'.format(cmd, process.returncode, stdoutdata, stderrdata))
        if process.returncode:
            print >> sys.stderr, 'Nonzero status {} for "{}": {}'.format(process.returncode, cmd, stderrdata)
        return process.returncode, stdoutdata, stderrdata
        
    def run_hdiutil_plist_command(self, cmd, input=None):
        status, stdoutdata, stderrdata = self.run_hdiutil_command(cmd, input=input)
        if status:
            return None
        data = plistlib.readPlistFromString(stdoutdata)
        return data


class AbstractSubcommand(object):

    def __init__(self, arguments):
        self.args = arguments

    def run(self):
        pass

    @classmethod
    def configure_argument_parser(cls, parser):
        pass

    @classmethod
    def subcommand_name(cls):
        return '-'.join([i.lower() for i in re.findall(r'([A-Z][a-z]+)', re.sub(r'^Subcommand', '', cls.__name__))])

    @classmethod
    def subclass_map(cls):
        map = {c.__name__: c for c in cls.__subclasses__()}
        for subclass in map.values():
            map.update(subclass.subclass_map())
        return map


class SubcommandInfo(AbstractSubcommand):
    """
    Print information about a disk image.
    """
    
    def run(self):
        image = DiskImage(self.args.dmg_url_or_path)
        print image.info()
    
    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('dmg_url_or_path', help='DMG URL or path')


class SubcommandInstallApplication(AbstractSubcommand):
    """
    Mount a DMG and install a toplevel .app into /Applications.
    """
    
    def run(self):
        image = DiskImage(self.args.dmg_url_or_path)
        print >> sys.stderr, 'Mounting {}...'.format(self.args.dmg_url_or_path)
        image.mount()
        print >> sys.stderr, 'Mounted at {}'.format(image.mount_point())
        self.install_apps_from_image_path(image.mount_point())
        image.unmount()

        if self.args.delete and not image.is_remote:
            self.trash_path(self.args.dmg_url_or_path)
    
    def install_apps_from_image_path(self, path):
        apps = glob.glob('{}/*.app'.format(path))
        if not apps:
            return
        
        for app_path in apps:
            basename = os.path.basename(app_path)
            destination_path = os.path.join('/Applications', basename)
            if os.path.exists(destination_path):
                self.trash_path(destination_path)
            self.copy_path(app_path, destination_path)

    def trash_path(self, path):
        basename = os.path.basename(path)
        user_trash_path = os.path.expanduser('~/.Trash')
        trash_path = os.path.join(user_trash_path, basename)
        if os.path.exists(trash_path):
            root, ext = os.path.splitext(basename)
            timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            trash_basename = '{}-{}{}'.format(root, timestamp, ext)
            trash_path = os.path.join(user_trash_path, trash_basename)
            print >> sys.stderr, 'Trashing {} to {}'.format(path, trash_path)
        else:
            print >> sys.stderr, 'Trashing {}'.format(path)
        shutil.move(path, trash_path)

    def copy_path(self, source_path, destination_path):        
        cmd = ['cp', '-pR', source_path, destination_path]
        process = subprocess.Popen(cmd)
        process.communicate()
    
    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('dmg_url_or_path', help='DMG URL or path')
        parser.add_argument('-d', '--delete', action='store_true', help='Delete disk image file after installation')


class ANSIColor(object):

    red = '1'
    green = '2'
    yellow = '3'
    blue = '4'

    @classmethod
    @contextlib.contextmanager
    def terminal_color(cls, stdout_color=None, stderr_color=red):

        if stdout_color:
            sys.stdout.write(cls.start_sequence(stdout_color))
        if stderr_color:
            sys.stderr.write(cls.start_sequence(stderr_color))

        try:
            yield
        except:
            cls.clear()
            raise

        cls.clear()

    @classmethod
    def clear(cls):
        for stream in [sys.stdout, sys.stderr]:
            stream.write(cls.clear_sequence())

    @classmethod
    def start_sequence(cls, color=red):
        return "\x1b[3{0}m".format(color)

    @classmethod
    def clear_sequence(cls):
        return "\x1b[m"

    @classmethod
    def wrap(cls, value, color=red):
        return u'{}{}{}'.format(cls.start_sequence(color), value, cls.clear_sequence())


class Tool(object):
    """Disk image utility"""

    def subcommand_map(self):
        return {s.subcommand_name(): s for s in AbstractSubcommand.subclass_map().values() if s.__name__.startswith('Subcommand')}

    def resolve_subcommand_abbreviation(self, subcommand_map):
        non_option_arguments = [i for i in sys.argv[1:] if not i.startswith('-')]
        if not non_option_arguments:
            return True

        subcommand = non_option_arguments[0]
        if subcommand in subcommand_map.keys():
            return True

        # converts a string like 'abc' to a regex like '(a).*?(b).*?(c)'
        regex = re.compile('.*?'.join(['(' + char + ')' for char in subcommand]))
        subcommand_candidates = []
        for subcommand_name in subcommand_map.keys():
            match = regex.match(subcommand_name)
            if not match:
                continue
            subcommand_candidates.append(self.subcommand_candidate_for_abbreviation_match(subcommand_name, match))

        if not subcommand_candidates:
            return True

        if len(subcommand_candidates) == 1:
            print >> sys.stderr, subcommand_candidates[0].decorated_name
            sys.argv[sys.argv.index(subcommand)] = subcommand_candidates[0].name
            return True

        print >> sys.stderr, 'Ambiguous subcommand "{}": {}'.format(subcommand, ', '.join([i.decorated_name for i in subcommand_candidates]))
        return False

    def subcommand_candidate_for_abbreviation_match(self, subcommand_name, match):
        SubcommandCandidate = collections.namedtuple('SubcommandCandidate', ['name', 'decorated_name'])
        decorated_name = ''
        for i in range(1, match.lastindex + 1):
            span = match.span(i)
            preceding = subcommand_name[match.span(i - 1)[1]:span[0]] if span[0] else ''
            letter = subcommand_name[span[0]:span[1]]
            decorated_name += preceding + ANSIColor.wrap(letter, color=ANSIColor.green)
        trailing = subcommand_name[span[1]:]
        decorated_name += trailing
        return SubcommandCandidate(subcommand_name, decorated_name)

    def configure_argument_parser(self, parser):
        pass

    def run(self):
        subcommand_map = self.subcommand_map()
        if not self.resolve_subcommand_abbreviation(subcommand_map):
            exit(1)

        parser = argparse.ArgumentParser(description=self.__doc__)
        self.configure_argument_parser(parser)
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')
        subparsers = parser.add_subparsers(title='Subcommands', dest='subcommand_name')
        for subcommand_name, subcommand_class in subcommand_map.items():
            subparser = subparsers.add_parser(subcommand_name, help=subcommand_class.__doc__)
            subcommand_class.configure_argument_parser(subparser)

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        subcommand_class = subcommand_map[args.subcommand_name]
        subcommand_class(args).run()

    @classmethod
    def ensure_superuser(cls):
        if os.getuid() != 0:
            print >> sys.stderr, 'Relaunching with sudo for superuser access'
            os.execv('/usr/bin/sudo', ['/usr/bin/sudo', '-E'] + sys.argv)

    @classmethod
    def main(cls):
        cls.ensure_superuser()
        try:
            cls().run()
        except KeyboardInterrupt:
            print >> sys.stderr, 'Interrupted'



if __name__ == "__main__":
    Tool.main()
