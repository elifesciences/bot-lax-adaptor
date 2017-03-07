#!/bin/bash
set -ev

# pass json objects to backfill script, one per line:
cat example.txt | jq . --compact-output | python src/backfill.py

# pass filenames to backfill script
python src/backfill.py article-xml/articles/elife-09560-v1.xml article-xml/articles/elife-09561-v1.xml
