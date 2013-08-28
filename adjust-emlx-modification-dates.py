#!/usr/bin/env python
#
# Adjust the file modification dates of OS X Mail.app .emlx files
# to match the date in their headers.
#
# Maintained at https://github.com/liyanage/macosx-shell-scripts/
#

import os
import argparse
import logging
import email.parser
import email.utils
import time


class MailMessageFile(object):
    
    def __init__(self, path):
        self.path = path
        self._header_date = None
        self._file_date = None
    
    def header_date(self):
        if not self._header_date:
            with open(self.path) as f:
                f.readline() # emlx files have an additional leading line
                message = email.parser.Parser().parse(f, headersonly=True)
                if not message:
                    logging.warning('Unable to parse emlx file as mail message: {}'.format(self.path))
                    return None
                date = message.get('date')
                if not date:
                    logging.warning('No date header found in {}'.format(self.path))
                    return None
                self._header_date = time.mktime(email.utils.parsedate(date))
        return self._header_date
    
    def file_date(self):
        if not self._file_date:
            self._file_date = os.path.getmtime(self.path)
        return self._file_date

    def has_date_mismatch(self, threshold_seconds=60):
        header_date = self.header_date()
        file_date = self.file_date()
        if not header_date and file_date:
            return None, True
        absdelta_seconds = int(abs(header_date - file_date))
        has_mismatch = absdelta_seconds > threshold_seconds
        return has_mismatch, None
    
    def fix_date(self):
        header_date = self.header_date()
        logging.debug('Changing date to {} for {}'.format(header_date, self.path))
        os.utime(self.path, (header_date, header_date))


class Tool(object):
    
    def __init__(self, mail_root, verbose=False):
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
        mail_root = os.path.expanduser(mail_root)
        assert os.path.exists(mail_root), 'Mail root directory {} does not exist.'.format(mail_root)
        self.mail_root = mail_root
        logging.debug('Mail root directory: {}'.format(mail_root))
    
    def adjust_dates(self, dry_run=False):
        for dirpath, dirnames, filenames in os.walk(self.mail_root):
            if 'Attachments' in dirnames:
                del(dirnames[dirnames.index('Attachments')])
            logging.info(dirpath)
            for filename in [f for f in filenames if f.endswith('.emlx')]:
                self.process_message_file(os.path.join(dirpath, filename), dry_run)

    def process_message_file(self, path, dry_run=False):
        message = MailMessageFile(path)
        has_mismatch, error = message.has_date_mismatch()
        if error or not has_mismatch:
            return
        logging.info('Found message with date mismatch: {}/{} {}'.format(message.header_date(), message.file_date(), path))
        if not dry_run:
            message.fix_date()
    
    @classmethod
    def run(cls):
        parser = argparse.ArgumentParser(description='Adjust the file modification dates of OS X Mail.app .emlx files to match the date in their headers.')
        parser.add_argument('mailroot', nargs='?', default='~/Library/Mail/V2/', help='Toplevel directory in which .emlx files should be changed. Defaults to ~/Library/Mail/V2')
        parser.add_argument('--dry-run', help='Dry run, list the affected files only', action='store_true')
        parser.add_argument('--verbose', help='Log debug output', action='store_true')
        args = parser.parse_args()
        Tool(args.mailroot, args.verbose).adjust_dates(dry_run=args.dry_run)

if __name__ == '__main__':
    Tool.run()
