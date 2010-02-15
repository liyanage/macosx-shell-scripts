#!/usr/bin/perl

use strict;
use warnings;
use XML::LibXML;
use IO::File;

# Location codes from http://weather.yahoo.com
my %cities = (
	"Zurich\t\t"      => '784794',
	"San Francisco\t" => '2487956',
);

my $report = "Current Temperature:\n";
while (my ($key, $value) = each %cities) {
	my $data = qx(curl -s http://weather.yahooapis.com/forecastrss?w=$value);
	unless ($data) {
		$report = 'Unable to get weather data';
		last;
	}
	my $doc = XML::LibXML->new()->parse_string($data);
	my ($temp) = $doc->findvalue('//yweather:condition/@temp');
	my $temp_c = int((5 / 9) * ($temp - 32));
	$report .= "$key ${temp}F ${temp_c}C\n";
}
my $pipe = IO::File->new("|/usr/local/bin/growlnotify --sticky --name '$0'");
$pipe->print($report);
$pipe->close();


__END__
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
	<dict>
		<key>KeepAlive</key>
		<false/>
		<key>Label</key>
		<string>Weather Summary</string>
		<key>ProgramArguments</key>
		<array>
			<string>/Users/liyanage/bin/weather-summary.pl</string>
		</array>
		<key>StartCalendarInterval</key>
		<dict>
			<key>Hour</key>
			<integer>10</integer>
		</dict>
		<key>RunAtLoad</key>
		<true/>
		<key>StandardErrorPath</key>
		<string>/dev/null</string>
		<key>StandardOutPath</key>
		<string>/dev/null</string>
	</dict>
</plist>
