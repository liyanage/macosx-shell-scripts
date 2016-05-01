#/bin/sh
#
# Export a given revision of the Git project in the current
# working directory into a directory on the desktop.
#
# Marc Liyanage <http://www.entropy.ch>
#

set -e

REVISION=$1
[ $REVISION ] || { echo Usage: $0 '<revision>'; false; }

git archive $REVISION | (cd ~/Desktop; mkdir "$REVISION" && cd "$REVISION" && tar -xf -)
