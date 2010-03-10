#!/usr/bin/perl
#
# Launch a Cocoa application with a given language localization
#
# Example:
#
#     launch-localized.pl Preferences de
# 
# opens the "System Preferences" application in German
#
# Written by Marc Liyanage <http://www.entropy.ch>
#

use strict;
use warnings;

my ($app, $language) = @ARGV;
die "Usage: $0 application [language]\n" unless $app;
$language ||= 'de';

my @paths = glob("/Applications/*$app*.app");
die "Application '$app' not found\n" unless @paths; 
die "'$app' ambiguous: @paths\n" if (@paths > 1); 
my ($path) = @paths;
my ($binary) = $path =~ m!/([^/]+).app$!;
my @cmd = ("$path/Contents/MacOS/$binary", '-AppleLanguages', "($language)");
print "@cmd\n";
system(@cmd);

