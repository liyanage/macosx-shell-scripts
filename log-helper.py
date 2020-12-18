#!/usr/bin/env python3

import sys
import argparse
import logging
from pathlib import Path
import subprocess
import datetime
import json
import copy
from typing import Optional


class Tool(object):

    def run(self):
        args = ['log', 'show'] + self.process_log_command_args()
        print(' '.join(args))
        subprocess.run(args)

    @classmethod
    def process_log_command_args(cls):
        args_out = []
        args_in = sys.argv[1:]

        timestamp_argument_indexes = []
        archive_path = None
        state = 'start'
        while args_in:
            arg = args_in.pop(0)

            if state == 'reading_archive_path':
                archive_path = Path(arg)
                assert archive_path.exists()
                state = 'start'
            elif state == 'reading_timestamp':
                timestamp_argument_indexes.append((len(args_out)))
                state = 'start'
            else:
                if arg == '--archive':
                    state = 'reading_archive_path'
                elif arg in ['--start', '--end']:
                    state = 'reading_timestamp'

            args_out.append(arg)
        
        timezone_delta = None
        if archive_path:
            timezone_delta = cls.timezone_delta_for_log_archive_path(archive_path)

        if timestamp_argument_indexes and timezone_delta:
            cls.update_timestamp_args(args_out, timestamp_argument_indexes, timezone_delta)

        return args_out

    @classmethod
    def update_timestamp_args(cls, args_out, timestamp_argument_indexes, timezone_delta):
        format = '%Y-%m-%d %H:%M:%S'
        for index in timestamp_argument_indexes:
            timestamp = datetime.datetime.strptime(args_out[index], format)
            adjusted_timestamp = timestamp - timezone_delta
            args_out[index] = adjusted_timestamp.strftime(format)

    @classmethod
    def timezone_delta_for_log_archive_path(cls, path: Path) -> Optional[datetime.timedelta]:
        first_line_timestamp_original = cls.timestamp_for_first_log_line(path, None)
        first_line_timestamp_local = cls.timestamp_for_first_log_line(path, 'local')

        if not (first_line_timestamp_original and first_line_timestamp_local):
            print('Unable to get timestamp from first log line', file=sys.stderr)
            return None

        # print('originator:', first_line_timestamp_original, first_line_timestamp_original.utcoffset())
        # print('local:', first_line_timestamp_local, first_line_timestamp_local.utcoffset())

        delta = first_line_timestamp_original.utcoffset() - first_line_timestamp_local.utcoffset()
        print('Timezone delta:', delta)
        return delta

    @classmethod
    def timestamp_for_first_log_line(cls, archive_path: str, timezone: str) -> Optional[datetime.datetime]:
        cmd = ['log', 'show', '--archive', archive_path, '--style', 'ndjson']
        if timezone:
            cmd.extend(['--timezone', timezone])
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        for line in process.stdout:
            record = json.loads(line)
            return cls.datetime_for_log_timestamp(record['timestamp'])
        return None

    @staticmethod
    def datetime_for_log_timestamp(log_timestamp):
        timestamp = log_timestamp[:29] + ':' + log_timestamp[29:]
        return datetime.datetime.fromisoformat(timestamp)


    @classmethod
    def main(cls):
        return cls().run()


if __name__ == "__main__":
    sys.exit(Tool.main())
