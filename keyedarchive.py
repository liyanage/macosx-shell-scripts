#!/usr/bin/env python
#
# Decode NSKeyedArchiver blobs for debugging purposes
#
# Written by Marc Liyanage
#
# See https://github.com/liyanage/macosx-shell-scripts
#

import os
import sys
import sqlite3
import argparse
import Foundation
import re
import objc
import base64
import collections
import tempfile
import subprocess
import logging
import zlib
import binascii
import textwrap


class KeyedArchiveObjectGraphNode(object):

    def __init__(self, identifier, serialized_representation, archive):
        self.identifier = identifier
        self.serialized_representation = serialized_representation
        self.archive = archive
    
    def resolve_references(self, archive):
        pass
    
    def dump_string(self, seen=None):
        raise Exception('{} must override dump_string()'.format(self.__class__))

    def indent(self, text):
        return ''.join(['|   ' + line for line in text.splitlines(True)])

    def indent_except_first(self, text, indent_count):
        lines = text.splitlines(True)
        if len(lines) < 2:
            return text
        indent = '|' + ' ' * (indent_count - 1)
        return ''.join(lines[:1] + [indent + line for line in lines[1:]])

    def wrap_text_to_line_length(self, text, length):
        return [text[i:i + length] for i in range(0, len(text), length)]

    def b64encode_and_wrap(self, bytes):
        dump = base64.b64encode(bytes)
        return '\n'.join(self.wrap_text_to_line_length(dump, 76))
    
    def hexencode_and_wrap(self, bytes):
        dump = binascii.hexlify(bytes)
        return '\n'.join(self.wrap_text_to_line_length(dump, 76))
    
    def ascii_dump_for_data(self, dump_bytes):
        length_limit = self.archive.input_output_configuration.output_dump_length()
        original_length = len(dump_bytes)
        if length_limit >= 0:
            dump_bytes = dump_bytes[:length_limit]
        truncated_length = len(dump_bytes)
        omitted_byte_count = original_length - truncated_length

        if self.archive.input_output_configuration.output_dump_encoding() == 'hex':
            ascii_dump = self.hexencode_and_wrap(dump_bytes)
        else:
            ascii_dump = self.b64encode_and_wrap(dump_bytes)
        
        if omitted_byte_count:
            ascii_dump += '\n[+ {} bytes]'.format(omitted_byte_count)
        
        return ascii_dump
    
    def __getitem__(self, key):
        raise Exception('{} must override __getitem__()'.format(self.__class__))
        
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return False
        
    @classmethod
    def parse_serialized_representation(cls, identifier, serialized_representation, archive):
        return cls(identifier, serialized_representation, archive)

    @classmethod
    def node_for_serialized_representation(cls, identifier, serialized_representation, archive):
        for node_class in cls.__subclasses__():
            if node_class.can_parse_serialized_representation(serialized_representation):
                return node_class.parse_serialized_representation(identifier, serialized_representation, archive)
        return None
    
    @classmethod
    def is_nsdictionary(cls, value):
        return hasattr(value, 'isNSDictionary__') and value.isNSDictionary__()
    
    @classmethod
    def is_nsdata(cls, value):
        return hasattr(value, 'isNSData__') and value.isNSData__()
    
    @classmethod
    def keyed_archiver_uid_for_value(cls, value):
        if hasattr(value, 'className') and value.className() == '__NSCFType':
            # TODO: find a non-hacky way to get at the value
            ids = re.findall(r'^<CFKeyedArchiverUID.+>\{value = (\d+)\}', unicode(value))
            if ids:
                return int(ids[0])
        return None
    

class KeyedArchiveObjectGraphNullNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return serialized_representation == '$null'
    
    def dump_string(self, seen=None):
        return '(null)'


class KeyedArchiveObjectGraphInstanceNode(KeyedArchiveObjectGraphNode):

    def __init__(self, identifier, serialized_representation, archive):
        self.properties = {}
        super(KeyedArchiveObjectGraphInstanceNode, self).__init__(identifier, serialized_representation, archive)
        for key, value in serialized_representation.items():
            if key == '$class':
                self.node_class = value
                continue
            self.properties[key] = value

    def resolve_references(self, archive):
        replacements = {}
        for key, value in self.properties.items():
            value = archive.replacement_object_for_value(value)
            if value:
                replacements[key] = value
        self.properties.update(replacements)

        self.node_class = archive.replacement_object_for_value(self.node_class)

    def dump_string(self, seen=None):
        if not seen:
            seen = set()
        if self in seen:
            return '<reference to {} id {}>'.format(self.node_class.dump_string(), self.identifier)
        seen.add(self)

        keys = self.properties.keys()
        instance_header = '<{} id {}>'.format(self.node_class.dump_string(), self.identifier)
        if not keys:
            instance_header += ' (empty)'
            return instance_header

        lines = [instance_header]
        max_key_len = max(map(len, keys))
        case_insensitive_sorted_property_items = sorted(self.properties.items(), key=lambda x: x[0], cmp=lambda a, b: cmp(a.lower(), b.lower()))
        for key, value in case_insensitive_sorted_property_items:
            if isinstance(value, KeyedArchiveObjectGraphNode):
#            if callable(getattr(value, 'dump_string', None)):
                description = value.dump_string(seen=seen)
            else:
                description = unicode(value)
            longest_key_padding = ' ' * (max_key_len - len(key))
            longest_key_value_indent = max_key_len + 2
            lines.append(self.indent(u'{}:{} {}'.format(key, longest_key_padding, self.indent_except_first(description, longest_key_value_indent))))
        
        return '\n'.join(lines)
    
    def __getitem__(self, key):
        if key not in self.properties:
            raise KeyError('Unknown key {}'.format(key))
        value = self.properties[key]
        if isinstance(value, KeyedArchiveObjectGraphNode):
            value = value.dump_string()
        return value
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return cls.is_nsdictionary(serialized_representation) and '$class' in serialized_representation

    @classmethod
    def parse_serialized_representation(cls, identifier, serialized_representation, archive):
        for node_class in cls.__subclasses__():
            if node_class.can_parse_serialized_representation(serialized_representation):
                return node_class.parse_serialized_representation(identifier, serialized_representation, archive)
        return super(KeyedArchiveObjectGraphInstanceNode, cls).parse_serialized_representation(identifier, serialized_representation, archive)


class KeyedArchiveObjectGraphNSDateNode(KeyedArchiveObjectGraphInstanceNode):
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return 'NS.time' in serialized_representation

    def dump_string(self, seen=None):
        return unicode(Foundation.NSDate.dateWithTimeIntervalSinceReferenceDate_(self.serialized_representation['NS.time']))


class KeyedArchiveObjectGraphNSMutableDataNode(KeyedArchiveObjectGraphInstanceNode):
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return 'NS.data' in serialized_representation

    def dump_string(self, seen=None):
        ascii_dump = self.ascii_dump_for_data(self.properties['NS.data'].bytes())
        return u'<NSMutableData length {}>\n{}'.format(self.properties['NS.data'].length(), ascii_dump)

    def resolve_references(self, archive):
        super(KeyedArchiveObjectGraphNSMutableDataNode, self).resolve_references(archive)
        data_value = self.serialized_representation['NS.data']
        if data_value:
            replacement = archive.replacement_object_for_value(data_value)
            if replacement:
                self.properties['NS.data'] = replacement.serialized_representation['NS.data']


class KeyedArchiveObjectGraphNSDataNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return cls.is_nsdata(serialized_representation)

    def dump_string(self, seen=None):
        ascii_dump = self.ascii_dump_for_data(self.serialized_representation.bytes())
        return u'<NSData length {}>\n{}'.format(self.serialized_representation.length(), ascii_dump)


class KeyedArchiveObjectGraphBoolNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return isinstance(serialized_representation, bool)

    def dump_string(self, seen=None):
        return 'True' if bool(self.serialized_representation) else 'False'


class KeyedArchiveObjectGraphLongNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return isinstance(serialized_representation, objc._pythonify.OC_PythonLong)

    def dump_string(self, seen=None):
        return str(self.serialized_representation)


class KeyedArchiveObjectGraphFloatNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return isinstance(serialized_representation, objc._pythonify.OC_PythonFloat)

    def dump_string(self, seen=None):
        return str(self.serialized_representation)


class KeyedArchiveObjectGraphNSMutableStringNode(KeyedArchiveObjectGraphInstanceNode):
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return 'NS.string' in serialized_representation

    def dump_string(self, seen=None):
        return self.serialized_representation['NS.string']


class KeyedArchiveObjectGraphNSDictionaryNode(KeyedArchiveObjectGraphInstanceNode):
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return 'NS.keys' in serialized_representation and 'NS.objects' in serialized_representation

    def resolve_references(self, archive):
        super(KeyedArchiveObjectGraphNSDictionaryNode, self).resolve_references(archive)

        dictionary = {}
        for index, key in enumerate(self.serialized_representation['NS.keys']):
            replacement_key = archive.replacement_object_for_value(key)
            if replacement_key:
                key = replacement_key.dump_string()
            value = self.serialized_representation['NS.objects'][index]
            replacement_value = archive.replacement_object_for_value(value)
            if replacement_value:
                value = replacement_value
            dictionary[key] = value
        self.properties.update(dictionary)
        del(self.properties['NS.keys'])
        del(self.properties['NS.objects'])


class KeyedArchiveObjectGraphNSArrayNode(KeyedArchiveObjectGraphInstanceNode):
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return 'NS.objects' in serialized_representation and 'NS.keys' not in serialized_representation

    def resolve_references(self, archive):
        super(KeyedArchiveObjectGraphNSArrayNode, self).resolve_references(archive)

        dictionary = {}
        fill = len(str(len(self.serialized_representation['NS.objects'])))
        for index, value in enumerate(self.serialized_representation['NS.objects']):
            replacement_value = archive.replacement_object_for_value(value)
            if replacement_value:
                value = replacement_value
            dictionary['{:0{fill}d}'.format(index, fill=fill)] = value
        self.properties.update(dictionary)
        del(self.properties['NS.objects'])


class KeyedArchiveObjectGraphClassNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return cls.is_nsdictionary(serialized_representation) and '$classname' in serialized_representation

    def dump_string(self):
        return self.serialized_representation['$classname']


class KeyedArchiveObjectGraphStringNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return isinstance(serialized_representation, basestring)

    def dump_string(self, seen=None):
        return unicode(self.serialized_representation)


class KeyedArchiveInputData(object):

    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.encoded_data = None
        self.decoded_data = None
        self.decode_data()
        
    def decode_data(self):
        self.encoded_data = self.raw_data
        self.decoded_data = self.raw_data
    
    def data(self):
        return self.decoded_data
    
    def encoded_data_length(self):
        if not self.encoded_data:
            return 0
        return len(self.encoded_data)
    
    def raw_data_is_ascii(self):
        try:
            self.raw_data.decode('ascii')
        except UnicodeDecodeError:
            return False
        return True
    
    @classmethod
    def priority(cls):
        return 0
    
    @classmethod
    def identifier(cls):
        return cls.__name__.replace('KeyedArchiveInputData', '').lower()
    
    @classmethod
    def guess_encoding(cls, data, encoding='auto'):
        if encoding == 'none':
            return cls(data)
        logging.debug('encoding: {}'.format(encoding))
        subclasses = cls.__subclasses__()

        if encoding == 'auto':
            items = []
            for subclass in subclasses:
                try:
                    item = subclass(data)
                    items.append(item)
                except:
                    pass
            
            def item_comparator(a, b):
                length_comparison = cmp(b.encoded_data_length(), a.encoded_data_length())
                if length_comparison != 0:
                    return length_comparison
                
                return cmp(b.priority(), a.priority())
            
            items = sorted(items, cmp=item_comparator)
            item = items[0]
            if items[0].encoded_data_length() == 0:
                # fall back to 'none'
                item = cls(data)
            logging.debug('Encoding "auto" picked encoding class {}'.format(type(item)))
            return item

        for subclass in subclasses:
            if subclass.identifier() == encoding:
                return subclass(data)
        
        raise Exception('Unable to determine input encoding')
        

class KeyedArchiveInputDataHex(KeyedArchiveInputData):
    
    def decode_data(self):
        if not self.raw_data_is_ascii():
            return

        regular_expressions = [r'<([A-Fa-f\s0-9]+)>', r'([A-Fa-f\s0-9]+)']
        for regex in regular_expressions:
            matches = re.findall(regex, self.raw_data, re.MULTILINE)
            if matches:
                matches = sorted(matches, key=len, reverse=True)
                data = matches[0]
                data = re.sub(r'\s+', '', data)
                self.encoded_data = data
                self.decoded_data = data.decode('hex')
                return

    @classmethod
    def priority(cls):
        return 1


class KeyedArchiveInputDataBase64(KeyedArchiveInputData):

    def decode_data(self):
        if not self.raw_data_is_ascii():
            return

        matches = re.findall(r'([A-Za-z\s0-9+/=]+)', self.raw_data, re.MULTILINE)
        if not matches:
            return

        if matches:
            matches = sorted(matches, key=len, reverse=True)
        
        data = matches[0]
        data = re.sub(r'\s+', '', data)
        self.encoded_data = data
        self.decoded_data = base64.b64decode(data)
        

class KeyedArchive(object):

    def __init__(self, archive_dictionary, configuration):
        self.archive_dictionary = archive_dictionary
        self.parse_archive_dictionary()
        self.input_output_configuration = configuration
    
    def parse_archive_dictionary(self):
        self.objects = []

        for index, obj in enumerate(self.archive_dictionary['$objects']):
            node = KeyedArchiveObjectGraphNode.node_for_serialized_representation(index, obj, self)
            if not node:
                raise Exception('Unable to parse serialized representation: {} / {}'.format(type(obj), obj))
            assert isinstance(node, KeyedArchiveObjectGraphNode)
            self.objects.append(node)

        for object in self.objects:
            object.resolve_references(self)
        
        self.top_object = self.object_at_index(self.top_object_identifier())
    
    def top_object_identifier(self):
        top_object_reference = self.archive_dictionary['$top']['root']
        top_object_identifier = KeyedArchiveObjectGraphNode.keyed_archiver_uid_for_value(top_object_reference)
        if top_object_identifier is None:
            raise Exception('Unable to find root object')
        return top_object_identifier
    
    def object_at_index(self, index):
        return self.objects[index]
    
    def dump_string(self):
        return self.top_object.dump_string()

    def replacement_object_for_value(self, value):
        id = KeyedArchiveObjectGraphNode.keyed_archiver_uid_for_value(value)
        if id is None:
            return None
        return self.object_at_index(id)
    
    @classmethod
    def archive_from_bytes(cls, archive_bytes, configuration):
        assert archive_bytes, 'Missing input data'
        archive_bytes = cls.process_data_for_input_configuration(archive_bytes, configuration)
        archive_dictionary, format, error = Foundation.NSPropertyListSerialization.propertyListWithData_options_format_error_(archive_bytes, 0, None, None)
        if not archive_dictionary:
            return None, error
        return cls(archive_dictionary, configuration), None

    @classmethod
    def archives_from_sqlite_table_column(cls, connection, table_name, column_name, extra_columns, extra_sql, configuration):
        columns = [column_name]
        if extra_columns:
            columns.extend(extra_columns)
        sql = 'SELECT {} FROM {} {}'.format(', '.join(columns), table_name, extra_sql)
        print sql
        cursor = connection.execute(sql)

        ArchiveDataRow = collections.namedtuple('ArchiveDataRow', 'archive extra_data error'.split())

        archives = []
        for row in cursor:
            archive_bytes, extra_fields = row[0], cls.sanitize_row(row[1:])
            archive = None
            error = None
            if archive_bytes:
                archive, error = cls.archive_from_bytes(archive_bytes, configuration)
            extra_data = dict(zip(extra_columns, extra_fields)) if extra_columns else None
            archive_data_row = ArchiveDataRow(archive, extra_data, error)
            archives.append(archive_data_row)
        return archives

    @classmethod
    def dump_archives_from_sqlite_table_column(cls, connection, table_name, column_name, extra_columns, extra_sql=''):
        rows = cls.archives_from_sqlite_table_column(connection, table_name, column_name, extra_columns, extra_sql)
        for row in rows:
            if row.extra_data:
                print row.extra_data
            if row.archive:
                print row.archive.dump_string()
            else:
                if row.extra_data:
                    print '(null)'
    
    @classmethod
    def sanitize_row(cls, row):
        return ['(null)' if i is None else i for i in row]

    @classmethod
    def dump_archive_from_plist_file(cls, plist_path, keypath, configuration):
        with open(plist_path) as f:
            bytes = f.read()
        assert bytes, 'Input file {} is empty'.format(plist_path)
        bytes = bytearray(bytes)

        plist_dictionary, format, error = Foundation.NSPropertyListSerialization.propertyListWithData_options_format_error_(bytes, 0, None, None)
        if not plist_dictionary:
            raise Exception('Unable to read property list from {}'.format(plist_dictionary))

        value = plist_dictionary.valueForKeyPath_(keypath)
        if not value:
            raise Exception('Unable to find value with key path {} from plist at {}'.format(keypath, plist_path))
        archive_bytes = value.bytes()

        if not len(archive_bytes):
            raise Exception('Encountered zero-length archived data bytes stream for key path {} from plist at {}'.format(keypath, plist_path))

        archive, error = cls.archive_from_bytes(archive_bytes, configuration)
        if not archive:
            with open('/tmp/dump.dat', 'w') as f:
                f.write(archive_bytes.tobytes())
            raise Exception('Unable to decode archive from data of length {} at key path {} from plist at {}'.format(len(archive_bytes), keypath, plist_path))
            
        print archive.dump_string()
    
    @classmethod
    def dump_archive_from_file(cls, archive_file, encoding, configuration, output_file=None):
        if not output_file:
            output_file = sys.stdout
        archive = cls.archive_from_file(archive_file, encoding, configuration)
        print >> output_file, archive.dump_string().encode('utf-8')

    @classmethod
    def archive_from_file(cls, archive_file, encoding, configuration):
        data = archive_file.read()
        
        data = KeyedArchiveInputData.guess_encoding(data, encoding)
        archive, error = cls.archive_from_bytes(data.data(), configuration)
        if not archive:
            if error:
                error = unicode(error).encode('utf-8')
            raise Exception('Unable to decode a keyed archive from input data: {}'.format(error))
        return archive

    @classmethod
    def process_data_for_input_configuration(cls, data, configuration):
        offset = configuration.input_data_offset()
        if offset:
            data = data[offset:]
        
        compression_type, options = configuration.input_data_compression_type_and_options()
        if compression_type:
            if compression_type == 'zlib':
                wbits = int(options) if options else 15
                compressed_length = len(data)
                data = zlib.decompress(memoryview(data).tobytes(), wbits)
                data = bytearray(data)
                decompressed_length = len(data)
                print 'Decompressed {} to {} bytes'.format(compressed_length, decompressed_length)
            else:
                raise Exception('Unsupported compression {}'.format(compression_type))

        return data


class InputOutputConfiguration(object):

    def output_dump_encoding(self):
        return 'hex'

    def output_dump_length(self):
        return 32
    
    def input_data_offset(self):
        return 0
    
    def input_data_compression_type_and_options(self):
        return None, None


class ArgumentParseInputOutputConfiguration(InputOutputConfiguration):

    def __init__(self, args):
        self.args = args
    
    def output_dump_encoding(self):
        return self.args.output_dump_encoding

    def output_dump_length(self):
        return self.args.output_dump_length
    
    def input_data_offset(self):
        return self.args.input_data_offset
    
    def input_data_compression_type_and_options(self):
        compression = self.args.input_data_compression
        if compression:
            match = re.match(r'(\w+)(?::(\w+))?', compression)
            assert match, 'Invalid compression option'
            return match.groups()
        return None, None


class KeyedArchiveTool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        if self.args.verbose:
            logging.basicConfig(level=logging.DEBUG)
    
        configuration = ArgumentParseInputOutputConfiguration(self.args)

        if self.args.service_mode:
            self.run_service(configuration)
        elif self.args.sqlite_path:
            self.run_sqlite(configuration)
        elif self.args.plist_path:
            self.run_plist(configuration)
        else:
            self.run_file(configuration)
        
    def run_sqlite(self, configuration):
        conn = sqlite3.connect(self.args.sqlite_path)
        KeyedArchive.dump_archives_from_sqlite_table_column(conn, self.args.sqlite_table, self.args.sqlite_column, self.args.extra_columns, self.args.extra_sql, configuration=configuration)

    def run_plist(self, configuration):
        KeyedArchive.dump_archive_from_plist_file(self.args.plist_path, self.args.plist_keypath, configuration=configuration)
    
    def run_file(self, configuration):
        if self.args.infile is None:
            self.parser().print_help()
            exit(0)
        KeyedArchive.dump_archive_from_file(self.args.infile, self.args.encoding, configuration)
    
    def run_service(self, configuration):
        temp = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        try:
            KeyedArchive.dump_archive_from_file(sys.stdin, self.args.encoding, configuration, output_file=temp)
        except Exception as e:
            temp.write('Unable to decode NSKeyedArchive: {}'.format(e))
        temp.close()
        subprocess.call(['open', '-a', 'Safari', temp.name])

    @classmethod
    def parser(cls):
        parser = argparse.ArgumentParser(
            description='NSKeyedArchive tool',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent('''\
                Examples
                --------
                
                keyedarchive.py -v --plist-path /path/to/plist --plist-keypath foo.bar.archive --input-data-offset 16 --input-data-compression zlib:31 --output-dump-encoding base64 --output-dump-length 200

                '''))
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable some additional debug logging output')

        input_output_configuration_group = parser.add_argument_group(title='Input/output options', description='Input/output configuration options')
        input_output_configuration_group.add_argument('--output-dump-length', type=int, default=32, help='Truncate binary data dumps to the given length. Defaults to 32. Set to -1 to allow unlimited length.')
        input_output_configuration_group.add_argument('--output-dump-encoding', choices=['base64', 'hex'], default='hex', help='ASCII format for binary data dumps. Defaults to "hex".')
        input_output_configuration_group.add_argument('--input-data-offset', type=int, help='Offset in bytes from the start of the byte stream to the start of the serialized keyed archiver data')
        input_output_configuration_group.add_argument('--input-data-compression', help='Decompression to apply to serialized keyed archiver data after applying offset and before unarchiving. The "zlib" format is currently the only supported format. You can add decompression options after a colon, for zlib the option is the "window bits" parameter, e.g. "zlib:31"')

        file_group = parser.add_argument_group(title='Reading from Files', description='Read the serialized archive from a file or stdin. The tool tries to guess the binary-to-text encoding, if any, unless one is chosen explicitly.')
        file_group.add_argument('infile', nargs='?', type=argparse.FileType('r'), help='The path to the input file. Pass - to read from stdin')
        file_group.add_argument('--encoding', choices='auto hex base64 none'.split(), default='auto', help='The binary-to-text encoding, if any. The default is auto.')
        file_group.add_argument('--service-mode', action='store_true', help='Enable OS X service mode. Take input from stdin with auto-detected encoding and write the result to a temporary text file and open it with Safari.')
        
        sqlite_group = parser.add_argument_group(title='Reading from SQLite databases', description='Read the serialized archive from SQLite DB. You need to pass at least the sqlite_path, sqlite_table, and sqlite_column options.')
        sqlite_group.add_argument('--sqlite-path', help='The path to the SQLite database file')
        sqlite_group.add_argument('--sqlite-table', help='SQLite DB table name')
        sqlite_group.add_argument('--sqlite-column', help='SQLite DB column name')
        sqlite_group.add_argument('--sqlite-extra-column', action='append', dest='extra_columns', help='additional column name, just for printing. Can occur multiple times.')
        sqlite_group.add_argument('--sqlite-extra-sql', dest='extra_sql', help='additional SQL code, e.g. for joins')

        plist_group = parser.add_argument_group(title='Reading from Property Lists', description='Read the serialized archive from a property list file, usually a preferences file in ~/Library/Preferences. You need to pass the plist_path and plist_keypath options.')
        plist_group.add_argument('--plist-path', help='The path to the plist file')
        plist_group.add_argument('--plist-keypath', help='The key/value coding key path to the object in the plist that contains the serialized keyed archiver data.')

        return parser

    @classmethod
    def main(cls):
        args = cls.parser().parse_args()
        if not args.verbose:
            sys.tracebacklimit = 0
        cls(args).run()

if __name__ == '__main__':
    KeyedArchiveTool.main()
