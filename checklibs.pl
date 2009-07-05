#!/usr/bin/perl
#
# Check the dynamic library dependencies of a
# Mac OS X binary.
# 
# See
#     http://www.entropy.ch/blog/Developer/2009/07/05/Updated-checklibs-pl-script-to-list-dynamic-library-dependencies.html
# for more information.
#
# Written by Marc Liyanage <http://www.entropy.ch>
#
#

use strict;
use warnings;

use Term::ANSIColor;

my ($file) = @ARGV;
die "Usage: $0 file\n" unless $file;

die $! unless (-f $file);

my $libs = {};
check_libs(file => $file, libs => $libs);

print
	map {(
		sprintf("\n%s:\n", colorize($_)),
		map {"\t$_\n"}
		map {colorize($_)}
		sort {lc($a) cmp lc($b)}
		@{$libs->{$_}}
	)}
	sort {lc($a) cmp lc($b)}
	grep {@{$libs->{$_}}}
	keys(%$libs);


sub check_libs {
	my (%args) = @_;
	my $libs = $args{libs};
	my @file_libs =
		grep {$_ ne $args{file}}
		grep {$_}
		map {/^\s+(\S+)/}
		qx(otool -L '$args{file}');
	$libs->{$args{file}} = \@file_libs;
	foreach my $lib (grep {!$libs->{$_}} @file_libs) {
		unless (-e $lib) {
			$libs->{$lib} = ['(missing)'];
			next;
		}
		check_libs(%args, file => $lib);		
	}
}


sub colorize {
	my ($path) = @_;
	return $path !~ m!^(/usr/lib|/System)! ? colored($path, 'red') : $path;
}
