#!/bin/sh

# See https://help.github.com/articles/installing-git-html-help
sudo mkdir -p /usr/local/git/share/doc
cd /usr/local/git/share/doc
if [ ! -e git-doc ]; then
	sudo git clone git://git.kernel.org/pub/scm/git/git-htmldocs.git git-doc
fi
cd git-doc
sudo git pull
