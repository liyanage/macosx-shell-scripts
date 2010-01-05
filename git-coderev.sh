#/bin/sh
#
# Compare two revisions of the Git project in the current working
# directory with coderev (http://code.google.com/p/coderev/) to
# produce an HTML report for code review.
#
# Marc Liyanage <http://www.entropy.ch>
#

CODEDIFF=/usr/local/coderev/codediff.py

set -e

REVISION1=$1
[ $REVISION1 ] || { echo Usage: $0 '<old_revision>' '[new_revision]'; echo "new_revision defaults to 'head'"; false; }
REVISION2=$2
[ $REVISION2 ] || { echo using head as new version; REVISION2=head; }

BRANCH=$(git status | grep 'On branch' | sed -e 's/.*branch //')
[ $BRANCH ] || { echo unable to determine branch; false; }
DIR=$(basename "$PWD")

git-export.sh "$REVISION1"
git-export.sh "$REVISION2"

git diff --stat "$REVISION1" "$REVISION2" > /tmp/diffstat.txt

$CODEDIFF \
-o ~/Desktop/"code review $DIR $BRANCH" \
--wrap=130 \
--commentfile=/tmp/diffstat.txt \
--title="Code changes for $DIR $BRANCH" \
~/Desktop/"$REVISION1" ~/Desktop/"$REVISION2"

rm -r ~/Desktop/"$REVISION1" ~/Desktop/"$REVISION2" /tmp/diffstat.txt