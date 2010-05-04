#!/usr/local/bin/macruby

if ARGV.empty?
  puts "Usage: unixtime.rb <unix-time-value>"
  exit
end

puts NSDate.dateWithTimeIntervalSince1970(ARGV[0]).description

