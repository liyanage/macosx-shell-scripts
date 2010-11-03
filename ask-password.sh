#!/bin/bash

set -e

PW=$(osascript <<EOF
tell application "System Events"
	activate
	text returned of (display dialog "Password:" default answer "" with hidden answer)
end tell
EOF
)

echo -n "$PW"

env > /tmp/askpass.txt
