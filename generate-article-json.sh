#!/bin/bash
# generates article-json from the contents of the elife-article-xml repo

set -e # everything must pass

. install.sh

echo > scrape.log

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

mkdir -p article-json
time python src/generate_article_json.py
