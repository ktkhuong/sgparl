@echo off
start cmd

start cmd /k "python todayonline.py -s 0 -e 250"
start cmd /k "python todayonline.py -s 250 -e 500"
start cmd /k "python todayonline.py -s 500 -e 750"
start cmd /k "python todayonline.py -s 750 -e 1000"
start cmd /k "python todayonline.py -s 1000 -e 1250"
start cmd /k "python todayonline.py -s 1500 -e 1681"