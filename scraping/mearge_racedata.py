# -*- coding: utf-8 -*-
import codecs
import re
import os
import sys
import math
import csv

all_races = []

for i in range(1, len(sys.argv)):
	with open(sys.argv[i], 'r') as csvfile:
		csvreader = csv.reader(csvfile)
		for race in csvreader:
			date = race[0].split('|')[-1]
			all_races.append((date, race))

all_races_s = sorted(all_races, key=lambda x: x[0])

all_races_u = []
all_races_h = {}

for i in range(len(all_races_s)):
	h = all_races_s[i][0]+','.join(all_races_s[i][1][1])
	if not h in all_races_h:
		all_races_h[h] = 1
		all_races_u.append(all_races_s[i][1])

with open('race_mearged.csv', 'w') as csvfile:
	csvwriter = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
	for i in range(len(all_races_u)):
		csvwriter.writerow(all_races_u[i])
	
