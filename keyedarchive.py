#!/usr/bin/env python
#
# Decode NSKeyedArchiver blobs for debugging purposes
#
# Written by Marc Liyanage
#
# See https://github.com/liyanage/macosx-shell-scripts
#

import sys
import sqlite3
import argparse
import Foundation
import re
import objc
import base64
import collections


class KeyedArchiveObjectGraphNode(object):

    def __init__(self, identifier, serialized_representation):
        self.identifier = identifier
        self.serialized_representation = serialized_representation
    
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
    
    def __getitem__(self, key):
        raise Exception('{} must override __getitem__()'.format(self.__class__))
        
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return False
        
    @classmethod
    def parse_serialized_representation(cls, identifier, serialized_representation):
        return cls(identifier, serialized_representation)

    @classmethod
    def node_for_serialized_representation(cls, identifier, serialized_representation):
        for node_class in cls.__subclasses__():
            if node_class.can_parse_serialized_representation(serialized_representation):
                return node_class.parse_serialized_representation(identifier, serialized_representation)
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


class KeyedArchiveObjectGraphInstanceNode(KeyedArchiveObjectGraphNode):

    def __init__(self, identifier, serialized_representation):
        self.properties = {}
        super(KeyedArchiveObjectGraphInstanceNode, self).__init__(identifier, serialized_representation)
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
    def parse_serialized_representation(cls, identifier, serialized_representation):
        for node_class in cls.__subclasses__():
            if node_class.can_parse_serialized_representation(serialized_representation):
                return node_class.parse_serialized_representation(identifier, serialized_representation)
        return super(KeyedArchiveObjectGraphInstanceNode, cls).parse_serialized_representation(identifier, serialized_representation)


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
        return u'<NSMutableData length {} bytes {}>'.format(self.serialized_representation['NS.data'].length(), base64.b64encode(self.serialized_representation['NS.data'].bytes()))


class KeyedArchiveObjectGraphNSDataNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return cls.is_nsdata(serialized_representation)

#     def resolve_references(self, archive):
#         super(KeyedArchiveObjectGraphNSDataNode, self).resolve_references(archive)
#         del(self.properties['NS.data'])

    def dump_string(self, seen=None):
        return u'<NSData length {} bytes {}>'.format(self.serialized_representation.length(), base64.b64encode(self.serialized_representation.bytes()))


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


class KeyedArchive(object):

    def __init__(self, archive_dictionary):
        self.archive_dictionary = archive_dictionary
        self.parse_archive_dictionary()
    
    def parse_archive_dictionary(self):
        self.objects = []

        for index, obj in enumerate(self.archive_dictionary['$objects']):
            node = KeyedArchiveObjectGraphNode.node_for_serialized_representation(index, obj)
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
        if not id:
            return None
        return self.object_at_index(id)
    
    @classmethod
    def archive_from_bytes(cls, bytes):
        assert bytes, 'Missing input data'
        archive_dictionary, format, error = Foundation.NSPropertyListSerialization.propertyListWithData_options_format_error_(bytes, 0, None, None)
        if not archive_dictionary:
            return None, error
        return cls(archive_dictionary), None

    @classmethod
    def archives_from_sqlite_table_column(cls, connection, table_name, column_name, extra_columns):
        columns = [column_name]
        if extra_columns:
            columns.extend(extra_columns)
        sql = 'SELECT {} FROM {}'.format(', '.join(columns), table_name)
        cursor = connection.execute(sql)

        ArchiveDataRow = collections.namedtuple('ArchiveDataRow', 'archive extra_data error'.split())

        archives = []
        for row in cursor:
            blob, extra_fields = row[0], cls.sanitize_row(row[1:])
            archive = None
            error = None
            if blob:
                archive, error = cls.archive_from_bytes(blob)
            archive_data_row = ArchiveDataRow(archive, dict(zip(extra_columns, extra_fields)), error)
            archives.append(archive_data_row)
        return archives

    @classmethod
    def dump_archives_from_sqlite_table_column(cls, connection, table_name, column_name, extra_columns):
        rows = cls.archives_from_sqlite_table_column(connection, table_name, column_name, extra_columns)
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


class KeyedArchiveTool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        if self.args.sqlite_filename:
            self.run_sqlite()
        
    def run_sqlite(self):
        conn = sqlite3.connect(self.args.sqlite_filename)
        KeyedArchive.dump_archives_from_sqlite_table_column(conn, self.args.sqlite_table, self.args.sqlite_column, self.args.extra_columns)

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='NSKeyedArchive tool')
        parser.add_argument('--sqlite_filename', help='SQLite DB filename')
        parser.add_argument('--sqlite_table', help='SQLite DB table name')
        parser.add_argument('--sqlite_column', help='SQLite DB column name')
        parser.add_argument('--sqlite_extra_column', action='append', dest='extra_columns', help='additional column name, just for printing. Can occur multiple times.')
        cls(parser.parse_args()).run()

if __name__ == '__main__':
    KeyedArchiveTool.main()
