#!/usr/bin/env python
#
# Reads the weather station list from http://weather.gov/xml/current_obs/index.xml
# and prints the stations sorted by distance to a given lat/long pair
#
# Usage:
# 
#     find-closest-noaa-weather-station.py <(curl -L http://weather.gov/xml/current_obs/index.xml) 37.7761965 -122.3947188
#
# Maintained at https://github.com/liyanage/macosx-shell-scripts
#

import sys
import math
import subprocess
import xml.etree.ElementTree

target_lat, target_lon = float(sys.argv[2]), float(sys.argv[3])
tree = xml.etree.ElementTree.parse(sys.argv[1])

station_map = {}
for station in tree.iter('station'):
    lat, lon = float(station.find('latitude').text), float(station.find('longitude').text)
    id = station.find('station_id').text
    name = station.find('station_name').text

    delta = abs(target_lat - lat) + abs(target_lon - lon)

    station_data = lat, lon, id, name, delta
    station_map[id] = station_data
    
stations_sorted = sorted(station_map.values(), cmp=lambda a, b: cmp(a[4], b[4]))
for lat, lon, id, name, delta in stations_sorted:
    print '{},{}\t{}\t{}'.format(lat, lon, id, name)
#    subprocess.call('curl http://w1.weather.gov/xml/current_obs/{}.xml'.format(id), shell=True)
