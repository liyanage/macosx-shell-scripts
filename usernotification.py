#!/usr/bin/env python
#
# Send OS X NSUserNotifications from Python.
#
# Written by Marc Liyanage
#
# https://github.com/liyanage/macosx-shell-scripts
#

import AppKit
import argparse


class UserNotification(object):
    
    def __init__(self, title, subtitle=None, informative_text=None, image_path=None):
        self.title = title
        self.subtitle = subtitle
        self.informative_text = informative_text
        self.image_path = image_path
    
    def post(self):
        notification = AppKit.NSUserNotification.alloc().init()
        notification.setTitle_(self.title)
        if self.subtitle:
            notification.setSubtitle_(self.subtitle)
        if self.informative_text:
            notification.setInformativeText_(self.informative_text)
        if self.image_path:
            image = AppKit.NSImage.alloc().initByReferencingFile_(self.image_path)
        
        center = AppKit.NSUserNotificationCenter.defaultUserNotificationCenter()
        center.scheduleNotification_(notification)
    
    def __unicode__(self):
        return u'<UserNotification title={} subtitle={} informative_text={}>'.format(self.title, self.subtitle, self.informative_text)

    def __str__(self):
        return unicode(self).encode('utf-8')


class UserNotificationTool(object):
    
    def __init__(self, args):
        self.args = args
    
    def post_notification(self):
        title = unicode(self.args.title, 'utf-8')
        subtitle = unicode(self.args.subtitle, 'utf-8') if self.args.subtitle else None
        informative_text = unicode(self.args.informative_text, 'utf-8') if self.args.informative_text else None
        image_path = unicode(self.args.image_path, 'utf-8') if self.args.image_path else None
        notification = UserNotification(title, subtitle=subtitle, informative_text=informative_text, image_path=image_path)
        notification.post()
        print notification
        
    
    @classmethod
    def run(cls):
        parser = argparse.ArgumentParser(description='Post Mac OS X user notifications')
        parser.add_argument('title', help='The notification title')
        parser.add_argument('subtitle', nargs='?', help='The notification subtitle')
        parser.add_argument('informative_text', nargs='?', help='The notification informative text')
        parser.add_argument('--image', dest='image_path', help='Optional Path to an image')

        args = parser.parse_args()
        tool = cls(args)
        tool.post_notification()


if __name__ == '__main__':
    UserNotificationTool.run()