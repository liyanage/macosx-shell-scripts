#!/usr/bin/env python3

import sys
import re
import dateparser
import datetime

r = re.compile(r'(\[../.../.... ..:..:..\])|(....-..-.....:..:..(?:\.\d+)?)')

while True:
    line = sys.stdin.readline()
    if not line:
        break
    match = r.search(line)
    if not match:
        continue
    value = next(e for e in match.groups() if e)
    parsed = dateparser.parse(value)
    if not parsed:
        continue

    shifted = parsed + datetime.timedelta(hours=-7)
    start, length = match.span()
    line_out = line[:start] + str(shifted) + line[length:]
    sys.stdout.write(line_out)
    sys.stdout.flush()
