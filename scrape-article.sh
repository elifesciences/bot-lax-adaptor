#!/bin/bash
# generate article-json from an xml article

set -e

if [ ! -d venv ]; then
    . install.sh > /dev/null
fi
source venv/bin/activate

if [ ! -d article-xml ]; then
    . download-elife-xml.sh &> /dev/null
fi

path_to_article_xml="$1"
if [ ! -e "$path_to_article_xml" ]; then
    echo "file not found"
    exit 1
fi

python src/main.py "$path_to_article_xml"
