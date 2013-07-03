#!/usr/bin/env python

import Foundation
import plistlib
import sys
import os
import objc

plist_path = sys.argv[1] if len(sys.argv) > 1 else None
if not plist_path:
    plist_path = os.path.join('/private/var/db/launchd.db', 'com.apple.launchd.peruser.{}'.format(os.getuid()), 'overrides.plist')

plist = plistlib.readPlist(plist_path)
for key, value in plist['_com.apple.SMLoginItemBookmarks'].items():
    print
    print key
    nsdata = Foundation.NSData.dataWithBytes_length_(value.data, len(value.data))
    url, isStale, error = Foundation.NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(nsdata, 0, None, None, None)
    if error:
        info = Foundation.NSURL.resourceValuesForKeys_fromBookmarkData_('_NSURLPathKey NSURLVolumeURLKey'.split(), nsdata)
        expected_path = info['_NSURLPathKey']
        print unicode(error).encode('utf-8')
        print 'Expected but not found at: {}'.format(expected_path)
    else:
        print 'Expected and found at: {}'.format(url.path())
    
    

