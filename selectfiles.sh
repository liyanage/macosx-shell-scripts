#!/bin/bash

osascript - <<EOF "$@"
on run argv
	set filesToSelect to {}
	repeat with filePath in argv
		set end of filesToSelect to posix file filePath
	end
	tell application "Finder"
		select filesToSelect
	end
	return
end
EOF

