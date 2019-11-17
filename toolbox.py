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
import zipfile
import shutil
import glob


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
        self.release = release
        self.preferred_asset_predicate = preferred_asset_predicate
        self.version_number_accessor = version_number_accessor
        self.cached_server_data = None
    
    def server_data(self):
        if not self.cached_server_data:
            try:
                url = 'https://api.github.com/repos/{}/{}/releases/{}'.format(self.repository.project, self.repository.repository, self.release)
                logging.debug('Loading {}'.format(url))            
                result = urllib2.urlopen(url)
                self.cached_server_data = json.load(result)
                assert 'assets' in self.cached_server_data, 'Unexpected data format: {}'.format(self.cached_server_data)
            except Exception as e:
                print('Unable to open URL {}: {}'.format(url, e), file=sys.stderr)
        return self.cached_server_data

    def version(self):
        logging.debug('GitHub release version() server data: {}'.format(self.server_data()))
        if not self.server_data():
            return None
        return pkg_resources.parse_version(self.version_number_accessor(self))

    def server_data_item(self, key):
        data = self.server_data()
        if not data:
            return None
        return data[key]

    def name(self):
        return self.server_data_item('name')
    
    @classmethod
    def version_number_accessor_for_server_data_item_regex(cls, data_item_key, regex):
        def accessor(release):
            result = re.findall(regex, release.server_data_item(data_item_key))
            assert result and len(result) == 1, 'Unable to find version number in "{}" using regex "{}"'.format(release.name(), regex)
            return result[0]
        return accessor

    def assets(self, predicate=None):
        assets = [GitHubReleaseAsset(asset_info) for asset_info in self.server_data()['assets']]
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

    tool_class_map = None

    @classmethod
    def tool_for_identifier(cls, identifier):
        if not cls.tool_class_map:
            cls.tool_class_map = {}
            for i, subclass in cls.enumerate_known_tool_classes():
                cls.tool_class_map[i] = subclass
                logging.debug('Subclass {} identifier {}'.format(subclass, i))
        if identifier not in cls.tool_class_map:
            raise Exception('Unable to find tool with identifier "{}"'.format(identifier))
        return cls.tool_class_map[identifier]()
    
    @classmethod
    def enumerate_known_tool_classes(cls):
        # This enumerates all descendant leaf classes but not abstract subclasses such as PKGBasedTool
        for subclass in cls.__subclasses__():
            if subclass.__subclasses__():
                for identifier, descendant in subclass.enumerate_known_tool_classes():
                    yield identifier, descendant
            else:
                yield subclass.identifier(), subclass

    @classmethod
    def enumerate_installed_tools(cls):
        installed_tools = []
        for i, subclass in cls.enumerate_known_tool_classes():
            tool = subclass()
            if tool.is_installed:
                yield i, tool

    @classmethod
    def known_identifiers(cls):
        return [i for i, _ in cls.enumerate_known_tool_classes()]

    @classmethod
    def identifier(cls):
        assert cls.__name__.startswith('Tool'), 'Class name of {} must start with "Tool" or class must override "identifier()"'
        return cls.__name__[len('Tool'):].lower()

    def is_installed(self):
        return self.installed_version() is not None
    
    def installed_version(self):
        raise Exception('"{}" must override this method'.format(type(self).__name__))

    def latest_version(self):
        raise Exception('"{}" must override this method'.format(type(self).__name__))
    
    def is_out_of_date(self):
        installed_version = self.installed_version()
        if not installed_version:
            print('Tool {} is not installed. Install it first with the "install" action.'.format(self.identifier()), file=sys.stderr)
            return False
        latest_version = self.latest_version()
        if not latest_version:
            print('Unable to check if {} is current because the latest version is unavailable'.format(self.identifier()), file=sys.stderr)
            return False
        return latest_version > installed_version
    
    def empty_install_staging_dir_path(self):
        temp_file_path = os.path.join(os.environ['TMPDIR'], 'toolbox.py-install-' + self.identifier())
        if os.path.exists(temp_file_path):
            shutil.rmtree(temp_file_path)
        os.mkdir(temp_file_path)
        return temp_file_path


    def install_latest_version(self):
        if not self.latest_version():
            print('Unable to install {} because the latest version is unavailable'.format(self.identifier()), file=sys.stderr)
            return False
        url = self.latest_version_archive_url()
        head, tail = os.path.split(url)
        temp_file_path = os.path.join(os.environ['TMPDIR'], tail)
        cmd = ['curl', '-L', '-o', temp_file_path, url]
        logging.debug('Download command: {}'.format(cmd))
        subprocess.check_call(cmd)
        self.install_archive(temp_file_path)
    
    @classmethod
    def have_dmgtool(cls):
        try:
            subprocess.check_call(['which', '-s', 'dmgtool.py'])
            return True
        except:
            return False

    @classmethod
    def dmgtool_install_package(cls, path):
        if cls.have_dmgtool():
            cmd = ['sudo', 'dmgtool.py', 'install-package', path]
            print(subprocess.check_output(cmd))
        else:
            print('dmgtool.py is not present (You can download it from https://github.com/liyanage/macosx-shell-scripts), please install package manually: {}'.format(path))

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
            assert len(version_matches) == 1, 'Unable to find version number in "{}" ({})'.format(version_string, len(version_matches))
            version_string = version_matches[0]
        return pkg_resources.parse_version(version_string)


class GitHubReleaseBasedTool(Tool):

    @classmethod
    def version_regex(cls):
        return r'\bv((?:[0-9]|\.)+)\b'

    def latest_version(self):
        return self.release.version()

    def latest_version_archive_url(self):
        return self.release.preferred_asset().download_url()


class ToolHugo(GitHubReleaseBasedTool):

    def __init__(self):
        self.repo = GitHubRepo('gohugoio', 'hugo')
        self.release = GitHubRelease(self.repo, 'latest',
            version_number_accessor=GitHubRelease.version_number_accessor_for_server_data_item_regex('name', self.version_regex()),
            preferred_asset_predicate=GitHubReleaseAsset.predicate_for_name_regex(r'extended_.*_macOS-64bit'))

    def installed_version(self):
        return self.version_from_process_output(['hugo', 'version'], self.version_regex())
    
    def install_archive(self, archive_path):
        archive = tarfile.open(archive_path)
        members = [m for m in archive.getmembers() if m.name == 'hugo']
        archive.extractall(path=os.path.expanduser('~/Documents/websites/hugo/'), members=members)


class ToolNinja(GitHubReleaseBasedTool):

    def __init__(self):
        self.repo = GitHubRepo('ninja-build', 'ninja')
        self.release = GitHubRelease(self.repo, 'latest',
            version_number_accessor=GitHubRelease.version_number_accessor_for_server_data_item_regex('tag_name', self.version_regex()),
            preferred_asset_predicate=GitHubReleaseAsset.predicate_for_name_regex(r'ninja-mac.zip'))

    def installed_version(self):
        return self.version_from_process_output(['ninja', '--version'], r'\b((?:[0-9]|\.)+)\b')
    
    def install_archive(self, archive_path):
        archive = zipfile.ZipFile(archive_path)
        archive.extractall(path=os.path.expanduser('~/bin/'), members=['ninja'])
        os.chmod(os.path.expanduser('~/bin/ninja'), 0755)


class ToolCmake(GitHubReleaseBasedTool):

    def __init__(self):
        self.repo = GitHubRepo('Kitware', 'CMake')
        self.release = GitHubRelease(self.repo, 'latest',
            version_number_accessor=GitHubRelease.version_number_accessor_for_server_data_item_regex('tag_name', self.version_regex()),
            preferred_asset_predicate=GitHubReleaseAsset.predicate_for_name_regex(r'cmake-\d+\.\d+.\d+-Darwin-x86_64.tar.gz'))

    def installed_version(self):
        return self.version_from_process_output(['cmake', '--version'], r'cmake version ((?:[0-9]|\.)+)')
    
    def install_archive(self, archive_path):
        archive = tarfile.open(archive_path)
        # logging.debug('archive members: {}'.format('\n'.join([ti.name for ti in archive.getmembers()])))
        staging_dir_path = self.empty_install_staging_dir_path()
        archive.extractall(path=staging_dir_path)
        app_paths = glob.glob(staging_dir_path + '/cmake-*Darwin*/CMake.app')
        assert len(app_paths) == 1, 'Unable to find app paths in "{}"'.format(staging_dir_path)
        app_path = app_paths[0]
        target_app_path = '/Applications/CMake.app'
        if os.path.exists(target_app_path):
            shutil.rmtree(target_app_path)
        shutil.move(app_path, target_app_path)


class ToolExifTool(Tool):

    def __init__(self):
        self.cached_server_data = None
        self.info_page_url = 'http://www.sno.phy.queensu.ca/~phil/exiftool/'
    
    def server_data(self):
        if not self.cached_server_data:
            try:
                request = urllib2.Request(self.info_page_url)
                response = urllib2.urlopen(request)
                data = response.read()
                results = re.findall(r'<a href="(ExifTool-([\d+.]+).dmg)">', data)
                if results:
                    self.cached_server_data = results[0]
                else:
                    print(data, file=sys.stderr)
                    print('Unable to find DMG link in page content of {}'.format(info_page_url), file=sys.stderr)
            except Exception as e:
                print('Unable to open URL {}: {}'.format(self.info_page_url, e), file=sys.stderr)
        return self.cached_server_data

    def installed_version(self):
        return self.version_from_process_output(['exiftool', '-ver'])

    def latest_version(self):
        data = self.server_data()
        if not data:
            return None
        return pkg_resources.parse_version(data[1])
    
    def latest_version_archive_url(self):
        data = self.server_data()
        if not data:
            return None
        dmg_filename = data[0]
        return self.info_page_url + dmg_filename

    def install_archive(self, archive_path):
        self.dmgtool_install_package(archive_path)


class PKGBasedTool(Tool):

    def latest_version(self):
        return pkg_resources.parse_version(self.server_version)
    
    def latest_version_archive_url(self):
        return self.archive_url

    def install_archive(self, archive_path):
        cmd = ['sudo', 'installer', '-pkg', archive_path, '-target', '/']
        print(subprocess.check_output(cmd))
    

class ToolPython3(PKGBasedTool):

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


class ToolNode(PKGBasedTool):

    def __init__(self):
        download_page_url = 'https://nodejs.org/en/'
        request = urllib2.Request(download_page_url)
        logging.debug('Loading {}'.format(download_page_url))
        response = urllib2.urlopen(request)
        self.data = response.read()
        result = re.findall(r'<a href="(https://nodejs\.org/dist/v.*?/)".*?title="Download .*?Current".*?data-version="v([0-9\.]+)', self.data)
        if not result:
            print(self.data)
            raise Exception('Unable to find pkg link in page content of {}'.format(download_page_url))
        self.archive_url, self.server_version = result[0]
        self.archive_url += 'node-v{}.pkg'.format(self.server_version)
    
    def installed_version(self):
        return self.version_from_process_output(['node', '--version'], r'v([0-9.]+)\b')


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

    def enumerate_selected_or_installed_tools(self):
        if self.args.tool_identifier:
            for i in self.args.tool_identifier:
                tool = Tool.tool_for_identifier(i)
                yield i, tool
        else:
            for tool in Tool.enumerate_installed_tools():
                yield tool


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
            print('Tool "{}", installed version: {}{}{}, latest version: {}'.format(identifier, color, v1, '\033[0m', v2))

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
            if tool.is_installed() and not tool.is_out_of_date() and not self.args.force:
                print('{} is current at version {}'.format(identifier, tool.installed_version()))
                continue
            tool.install_latest_version()

    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('tool_identifier', nargs='*', help='Identifier of the tool to update. Optional, defaults to all known tools.')
        parser.add_argument('-f', '--force', action='store_true', help='Force update even if the installed version is up to date')


class SubcommandUpdate(AbstractSubcommand):
    """
    Install or update a tool
    """
    
    def run(self):
        for identifier, tool in self.enumerate_selected_or_installed_tools():
            logging.debug('Installed version: {}, current version: {}'.format(tool.installed_version(), tool.latest_version()))
            if not tool.is_out_of_date() and not self.args.force:
                continue
            tool.install_latest_version()

    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('tool_identifier', nargs='*', help='Identifier of the tool to update. Optional, defaults to all installed tools.')
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
