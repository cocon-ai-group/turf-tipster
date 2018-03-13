#!/bin/bash

python3 scraping.py
python3 scraping2.py

python3 mearge_racedata.py race_database.csv race_database2.csv

wc -l race_mearged.csv

tail -n3000 race_mearged.csv | head -n2500 > race_train.csv
tail -n3000 race_mearged.csv | tail -n500 > race_test.csv

# to validation
# python3 train.py -t race_train.csv -e race_test.csv

# to train
# python3 train.py -t race_mearged.csv -e race_test.csv
