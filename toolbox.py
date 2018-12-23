#!/usr/bin/env python


from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division
from __future__ import print_function

import sys
import os
import re
import argparse
import logging
import subprocess
import pkg_resources
import urllib2
import json
import tarfile


class GitHubReleaseAsset(object):

    def __init__(self, asset_info):
        self.asset_info = asset_info
    
    def name(self):
        return self.asset_info['name']
    
    def download_url(self):
        return self.asset_info['browser_download_url']

    @classmethod
    def predicate_for_name_regex(cls, regex):
        def predicate(asset):
            if re.search(regex, asset.name()):
                return True
        return predicate


class GitHubRelease(object):

    def __init__(self, repository, release, version_number_accessor, preferred_asset_predicate=None):
        self.repository = repository
        self.preferred_asset_predicate = preferred_asset_predicate
        self.version_number_accessor = version_number_accessor
        url = 'https://api.github.com/repos/{}/{}/releases/{}'.format(repository.project, repository.repository, release)
        logging.debug('Loading {}'.format(url))            
        result = urllib2.urlopen(url)
        self.data = json.load(result)
        assert 'assets' in self.data, 'Unexpected data format: {}'.format(self.data)
    
    def version(self):
        return pkg_resources.parse_version(self.version_number_accessor(self))
    
    def name(self):
        return self.data['name']
    
    @classmethod
    def version_number_accessor_for_name_regex(cls, regex):
        def accessor(release):
            result = re.findall(regex, release.name())
            assert result and len(result) == 1, 'Unable to find version number in "{}" using regex "{}"'.format(release.name(), regex)
            return result[0]
        return accessor

    def assets(self, predicate=None):
        assets = [GitHubReleaseAsset(asset_info) for asset_info in self.data['assets']]
        if predicate:
            assets = [a for a in assets if predicate(a)]
        return assets

    def preferred_asset(self):
        assert self.preferred_asset_predicate
        assets = self.assets(predicate=self.preferred_asset_predicate)
        assert len(assets) == 1
        return assets[0]


class GitHubRepo(object):

    def __init__(self, project, repository):
        self.project = project
        self.repository = repository


class Tool(object):

    @classmethod
    def tool_for_identifier(cls, identifier):
        for i, subclass in cls.enumerate_known_tools():
            logging.debug('Subclass {} identifier {}'.format(subclass, i))
            if i == identifier:
                return subclass()
        raise Exception('Unable to find tool with identifier "{}"'.format(identifier))
    
    @classmethod
    def enumerate_known_tools(cls):
        for subclass in cls.__subclasses__():
            yield subclass.identifier(), subclass
    
    @classmethod
    def known_identifiers(cls):
        return [s.identifier() for s in cls.__subclasses__()]

    @classmethod
    def identifier(cls):
        assert cls.__name__.startswith('Tool'), 'Class name of {} must start with "Tool" or class must override "identifier()"'
        return cls.__name__[len('Tool'):].lower()
    
    def installed_version(self):
        raise Exception('"{}" must override this method'.format(type(self).__name__))

    def latest_version(self):
        raise Exception('"{}" must override this method'.format(type(self).__name__))
    
    def is_current(self):
        installed_version = self.installed_version()
        if installed_version:
            return installed_version >= self.latest_version()
        return False
    
    def install_latest_version(self):
        url = self.latest_version_archive_url()
        head, tail = os.path.split(url)
        temp_file_path = os.path.join(os.environ['TMPDIR'], tail)
        cmd = ['curl', '-L', '-o', temp_file_path, url]
        logging.debug('Download command: {}'.format(cmd))
        subprocess.check_call(cmd)
        self.install_archive(temp_file_path)
    
    def install_archive(self, archive_path):
        raise Exception('"{}" must override this method'.format(type(self).__name__))

    def latest_version_archive_url(self):
        raise Exception('"{}" must override this method'.format(type(self).__name__))
    
    @classmethod
    def version_from_process_output(cls, cmd, regex=None):
        try:
            version_string = subprocess.check_output(cmd).strip()
        except Exception as e:
            return None        
        if regex:
            version_matches = re.findall(regex, version_string)
            assert len(version_matches) == 1, 'Unable to find version number in "{}"'.format(version_string)
            version_string = version_matches[0]
        return pkg_resources.parse_version(version_string)


class ToolHugo(Tool):

    def __init__(self):
        self.repo = GitHubRepo('gohugoio', 'hugo')
        self.release = GitHubRelease(self.repo, 'latest',
            version_number_accessor=GitHubRelease.version_number_accessor_for_name_regex(self.version_regex()),
            preferred_asset_predicate=GitHubReleaseAsset.predicate_for_name_regex(r'extended_.*_macOS-64bit'))

    def installed_version(self):
        return self.version_from_process_output(['hugo', 'version'], self.version_regex())
    
    @classmethod
    def version_regex(cls):
        return r'\bv((?:[0-9]|\.)+)\b'

    def latest_version(self):
        return self.release.version()

    def latest_version_archive_url(self):
        return self.release.preferred_asset().download_url()

    def install_archive(self, archive_path):
        archive = tarfile.open(archive_path)
        members = [m for m in archive.getmembers() if m.name == 'hugo']
        archive.extractall(path=os.path.expanduser('~/Documents/websites/hugo/'), members=members)


class ToolExifTool(Tool):

    def __init__(self):
        info_page_url = 'http://www.sno.phy.queensu.ca/~phil/exiftool/'
        request = urllib2.Request(info_page_url)
        response = urllib2.urlopen(request)
        self.data = response.read()
        result = re.findall(r'<a href="(ExifTool-([\d+.]+).dmg)">', self.data)
        if not result:
            print(self.data)
            raise('Unable to find DMG link in page content of {}'.format(info_page_url))
        self.dmg_filename, self.server_version = result[0]
        self.dmg_url = info_page_url + self.dmg_filename
    
    def installed_version(self):
        return self.version_from_process_output(['exiftool', '-ver'])

    def latest_version(self):
        return pkg_resources.parse_version(self.server_version)
    
    def latest_version_archive_url(self):
        return self.dmg_url

    def install_archive(self, archive_path):
        cmd = ['sudo', 'dmgtool.py', 'install-package', archive_path]
        print(subprocess.check_output(cmd))


class ToolPython3(Tool):

    def __init__(self):
        download_page_url = 'https://www.python.org/downloads/'
        request = urllib2.Request(download_page_url)
        response = urllib2.urlopen(request)
        self.data = response.read()
        result = re.findall(r'href="(.*/python-([\d+.]+).*pkg)">Download Python 3', self.data)
        if not result:
            print(self.data)
            raise('Unable to find pkg link in page content of {}'.format(download_page_url))
        self.archive_url, self.server_version = result[0]
    
    def installed_version(self):
        return self.version_from_process_output(['python3', '-V'], r'\b([0-9.]+)\b')

    def latest_version(self):
        return pkg_resources.parse_version(self.server_version)
    
    def latest_version_archive_url(self):
        return self.archive_url

    def install_archive(self, archive_path):
        cmd = ['sudo', 'installer', '-pkg', archive_path, '-target', '/']
        print(subprocess.check_output(cmd))



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
    
    def selected_or_all_tool_identifiers(self):
        if self.args.tool_identifier:
            return self.args.tool_identifier
        else:
            return Tool.known_identifiers()


class SubcommandStatus(AbstractSubcommand):
    """
    Show status of a tool
    """
    
    def run(self):
        for identifier in self.selected_or_all_tool_identifiers():
            tool = Tool.tool_for_identifier(identifier)
            v1 = tool.installed_version()
            v2 = tool.latest_version()
            if v1 == v2:
                color = '\033[0;32m'
            else:
                color = '\033[0;31m'
            print('Tool "{}", installed version: {}{}{}, latest version: {}'.format(identifier, color, tool.installed_version(), '\033[0m', tool.latest_version()))            

    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('tool_identifier', nargs='*', help='Identifier of the tool to update')


class SubcommandInstall(AbstractSubcommand):
    """
    Install or update a tool
    """
    
    def run(self):
        for identifier in self.selected_or_all_tool_identifiers():
            logging.debug('Searching for tool with identifier {}'.format(identifier))
            tool = Tool.tool_for_identifier(identifier)
            logging.debug('Installed version: {}, current version: {}'.format(tool.installed_version(), tool.latest_version()))            
            if tool.is_current() and not self.args.force:
                print('{} is current at version {}'.format(identifier, tool.installed_version()))
                continue
            tool.install_latest_version()

    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('tool_identifier', nargs='*', help='Identifier of the tool to update')
        parser.add_argument('-f', '--force', action='store_true', help='Force update even if the installed version is up to date')


class CommandLineDriver(object):

    def subcommand_map(self):
        return {subclass.subcommand_name(): subclass for subclass in AbstractSubcommand.__subclasses__()}

    @classmethod
    def main(cls):
        cls().run()

    def run(self):
        parser = argparse.ArgumentParser(description='Manage some external tools not supplied with the OS')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')
        subparsers = parser.add_subparsers(title='Subcommands', dest='subcommand_name')

        subcommand_map = self.subcommand_map()
        for subcommand_name, subcommand_class in subcommand_map.items():
            subparser = subparsers.add_parser(subcommand_name, help=subcommand_class.__doc__)
            subcommand_class.configure_argument_parser(subparser)

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        subcommand_class = subcommand_map[args.subcommand_name]
        subcommand_class(args).run()


if __name__ == "__main__":
    CommandLineDriver.main()
