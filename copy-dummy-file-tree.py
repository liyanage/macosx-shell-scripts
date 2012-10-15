#!/usr/bin/env python

# Copies a directory tree, but all files will be zero-length placeholder/dummy files.

import os, sys

input_dir, output_dir_parent = sys.argv[1:3]
print input_dir, output_dir_parent

input_dir_parent = os.path.dirname(input_dir)

for root, dirs, files in os.walk(input_dir):
	for dir in dirs:
		subdir = os.path.join(root, dir)
		output_subdir = os.path.normpath(subdir.replace(input_dir_parent, output_dir_parent))
 		output_subdir = os.path.normpath('/'.join((output_dir_parent, subdir.replace(input_dir_parent, ''))))
 		if not os.path.exists(output_subdir):
 			os.makedirs(output_subdir)

	for filename in files:
		if filename.startswith("."):
			continue
		filepath = os.path.join(root, filename)
		output_filepath = os.path.normpath(filepath.replace(input_dir_parent, output_dir_parent))
 		with file(output_filepath, 'a'):
 			pass
