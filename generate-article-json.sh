#!/bin/bash
set -e
source download-elife-xml.sh
mkdir -p article-json
echo > scrape.log

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

for i in `ls ./article-xml/articles/*.xml | sort -r`; do 
    echo $i
    python ./src/main.py $i > ./article-json/$(basename $i).json 2> /dev/null || {
        
        echo "scraping failed, grep scrape.log for " $(basename $i)
    }
done
