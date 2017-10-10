#!/bin/sh

find $(dirname $TMPDIR)/C -type d -name Shared* -exec rm -r {} \; -prune
find ~/Library/Developer/Xcode/DerivedData -type d -name PrecompiledHeaders -exec rm -rf {} \; -prune

