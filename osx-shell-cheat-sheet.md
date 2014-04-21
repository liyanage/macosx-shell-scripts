
Some useful shell (usually bash) snippets, some OS X-specific, some not.

# Checksum for all files in a directory tree

    find /path/to/dir -type f -exec md5 -r {} + | awk '{print $1}' | sort | md5

From http://stackoverflow.com/questions/1657232/how-can-i-calculate-an-md5-checksum-of-a-directory

