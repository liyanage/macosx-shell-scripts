#!/bin/sh
# 
# Update both Git and the Git HTML docs (for indexing using LaunchBar)
#

set -e

# See https://help.github.com/articles/installing-git-html-help
sudo mkdir -p /usr/local/git/share/doc
cd /usr/local/git/share/doc
if [ ! -e git-doc ]; then
	sudo git clone git://git.kernel.org/pub/scm/git/git-htmldocs.git git-doc
fi
cd git-doc
sudo git pull

GIT_DOWNLOAD_PAGE_URL=http://git-scm.com/download/mac
GIT_DMG_URL=$(curl -s $GIT_DOWNLOAD_PAGE_URL | grep https://git-osx-installer | sed -E 's#.*(https://.*.dmg).*#\1#' | uniq)
[ -z $GIT_DMG_URL ] && { echo Unable to find Git DMG URL on $GIT_DOWNLOAD_PAGE_URL; false; }

GIT_DMG=$TMPDIR/git.dmg
curl -o $GIT_DMG $GIT_DMG_URL

VOLUME_PATH=$(hdiutil attach $GIT_DMG | grep /Volumes | sed -E 's#.*(/Volumes.*)#\1#')
[ -e "$VOLUME_PATH" ] || { echo Unable to mount $GIT_DMG, volume not found; false; }
GIT_PKG_PATH=$(echo "$VOLUME_PATH"/*.pkg)
sudo installer -pkg "$GIT_PKG_PATH" -target /
hdiutil unmount "$VOLUME_PATH" 
