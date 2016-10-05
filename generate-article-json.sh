#!/bin/bash
# generates article-json from the contents of the elife-article-xml repo

set -e # everything must pass
. download-elife-xml.sh
echo > scrape.log

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

mkdir -p article-json
for i in `ls ./article-xml/articles/*.xml | sort -r`; do 
    echo $(basename $i) "-> " $(basename $i).json
    python ./src/main.py $i > ./article-json/$(basename $i).json 2> /dev/null || {
        
        echo "scraping failed, grep scrape.log for " $(basename $i)
    }
done
