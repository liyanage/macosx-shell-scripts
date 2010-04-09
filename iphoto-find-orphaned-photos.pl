#!/usr/bin/perl
#

use strict;
use warnings;
use URI::Escape;
use File::Basename;


exit Tool->new(@ARGV)->run();


package Tool;

sub new {
	my $class = shift;
	my %args = @_;
	return bless \%args, $class;
}

sub run {
	my $self = shift;

	my @db_paths =
		grep {-e}
		map {File::Basename::dirname($_) . '/iPhotoMain.db'}
		map {URI::Escape::uri_unescape($_)}
		qx(defaults read "$ENV{HOME}/Library/Preferences/com.apple.iApps" iPhotoRecentDatabases) =~ m!file://localhost(.+)"!g;

	$self->find_orphaned_in_db($_) foreach @db_paths;
	return 0;
}

sub find_orphaned_in_db {
	my $self = shift;
	my ($db_path) = @_;
	
	my $aux_path = File::Basename::dirname($db_path) . "/iPhotoAux.db";
	
	my $cmd = "sqlite3 '$db_path' 'SELECT finfo.relativePath, fimg.photoKey FROM SqFileInfo finfo JOIN SQFileImage fimg ON finfo.primaryKey = fimg.sqFileInfo WHERE fimg.imageType = 6;'";
	my @rows = split(/\n/, qx($cmd));
	foreach my $row (@rows) {
		my ($path, $photo_id) = split(/\|/, $row);
		next if (-e $path);
		print "sqlite3 '$db_path' 'DELETE FROM SqPhotoInfo WHERE primaryKey = $photo_id'\n";
		print "sqlite3 '$db_path' 'DELETE FROM AlbumsPhotosJoin WHERE sqPhotoInfo = $photo_id'\n";
		print "sqlite3 '$db_path' 'DELETE FROM KeywordsPhotosJoin WHERE sqPhotoInfo = $photo_id'\n";
		print "sqlite3 '$db_path' 'DELETE FROM SqFileInfo WHERE primaryKey IN (SELECT sqFileInfo FROM SqFileImage WHERE photoKey = $photo_id)'\n";
		print "sqlite3 '$db_path' 'DELETE FROM SqFileImage WHERE photoKey = $photo_id'\n";
		print "sqlite3 '$aux_path' 'DELETE FROM SQPhotoInfoEdit WHERE primaryKey = $photo_id; DELETE FROM SqPhotoInfoExif2 WHERE primaryKey = $photo_id; DELETE FROM SqPhotoInfoOld WHERE primaryKey = $photo_id; DELETE FROM SqPhotoInfoOther WHERE primaryKey = $photo_id'\n";
		print "\n";
	}
}

