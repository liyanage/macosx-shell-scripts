#!/bin/sh

#date >> /tmp/scansnap

ps ax | grep -v grep | grep -qc ScanSnap
SCANSNAP_APP_RUNNING=$?

ioreg | grep -qc ScanSnap
SCANSNAP_HARDWARE_PRESENT=$?

if [ $SCANSNAP_APP_RUNNING -eq 0 -a $SCANSNAP_HARDWARE_PRESENT -ne 0 ]; then
#	echo app running but scanner not present >> /tmp/scansnap
	PID=$(ps -axo pid,comm | grep 'ScanSnap Manager' | cut -f 1 -d ' ')
	kill $PID
fi

if [ $SCANSNAP_APP_RUNNING -ne 0 -a $SCANSNAP_HARDWARE_PRESENT -eq 0 ]; then
#	echo app not running but scanner present >> /tmp/scansnap
	open -a 'ScanSnap Manager'
fi

