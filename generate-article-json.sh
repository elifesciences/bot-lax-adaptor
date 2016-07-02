#!/bin/bash
set -e
source download-elife-xml.sh
mkdir -p article-json
for i in `ls ./article-xml/articles/*.xml | sort -r`; do 
    echo $i
    python ./src/main.py $i > ./article-json/$(basename $i).json
done
