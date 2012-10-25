#!/usr/bin/env python

# Example for posting an OS X 10.8 User Notification from Python/shell scripts

import Cocoa
import sys

notification = Cocoa.NSUserNotification.alloc().init()
notification.setTitle_(sys.argv[1])
center = Cocoa.NSUserNotificationCenter.defaultUserNotificationCenter()
center.scheduleNotification_(notification)

