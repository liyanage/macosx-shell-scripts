#!/usr/bin/env python

# Listen for and dump NSDistributedNotifications
#
# Maintainted at https://github.com/liyanage/macosx-shell-scripts

import objc
import datetime
import Foundation

class DistributedNotificationListener(object):

    def __init__(self):
        self.should_terminate = False

    def run(self):
        center = Foundation.NSDistributedNotificationCenter.defaultCenter()
        selector = objc.selector(self.didReceiveNotification_, signature='v@:@')
        center.addObserver_selector_name_object_suspensionBehavior_(self, selector, None, None, Foundation.NSNotificationSuspensionBehaviorDeliverImmediately)
        runloop = Foundation.NSRunLoop.currentRunLoop()
        
        while not self.should_terminate:
            runloop.runUntilDate_(Foundation.NSDate.dateWithTimeIntervalSinceNow_(1))
    
    def didReceiveNotification_(self, notification):
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        print '{} name={} object={} userInfo={}'.format(timestamp, notification.name(), notification.object(), notification.userInfo())

    def terminate(self):
        print 'Stopping'
        self.should_terminate = True
    
    @classmethod
    def main(cls):
        listener = cls()
        try:
            listener.run()
        except KeyboardInterrupt:
            listener.terminate()

if __name__ == '__main__':
    DistributedNotificationListener.main()
