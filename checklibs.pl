#!/usr/bin/perl
#
# Check the dynamic library dependencies of a
# Mac OS X binary
#
# Written by Marc Liyanage <http://www.entropy.ch>
#
#

use strict;
use warnings;


my ($file) = @ARGV;
die "Usage: $0 file\n" unless $file;

die $! unless (-f $file);

my $libs = {};
check_libs(file => $file, libs => $libs);

print
	map {("\n$_:\n", map {"\t$_\n"} sort {lc($a) cmp lc($b)} @{$libs->{$_}})}
	sort {lc($a) cmp lc($b)}
	grep {@{$libs->{$_}}}
	keys(%$libs);

sub check_libs {
	my (%args) = @_;
	my $libs = $args{libs};
	my @file_libs = grep {$_ ne $args{file}} grep {$_} map {/^\s+(\S+)/} qx(otool -L '$args{file}');
	$libs->{$args{file}} = \@file_libs;
	foreach my $lib (grep {!$libs->{$_}} @file_libs) {
		unless (-f $lib) {
			$libs->{$lib} = ['(missing)'];
			next;
		}
		check_libs(%args, file => $lib);		
	}
}


