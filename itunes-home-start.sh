#!/bin/sh
#
# Set up Bonjour Forwarding to home Mac through SSH and MobileMe Back to my Mac
#
# Info from:
# - http://blog.iharder.net/2009/09/28/itunes-stream-itunes-over-ssh/
# - http://lists.apple.com/archives/bonjour-dev/2007/Jul/msg00031.html
#
dns-sd -P "Marc’s Home iTunes" _daap._tcp . 13689 something.local 127.0.0.1 "Arbitrary text record" &
#dns-sd -P "Marc’s Home iTunes" _daap._tcp . 13689 something.local minime-marc.liyanage.members.mac.com. 3689 "Arbitrary text record" &
PID=$!
#/opt/local/bin/socat TCP4-LISTEN:13689,reuseaddr,fork TCP6:minime-marc.liyanage.members.mac.com:3689
ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=99 -C -N -L *:13689:localhost:3689 -6 minime-marc.liyanage.members.mac.com.
#ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=99 -C -N -L *:13689:localhost:3689 -6 fd2f:1af4:df9:39:216:cbff:fea2:79f2
kill $PID
