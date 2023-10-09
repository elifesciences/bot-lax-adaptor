#!/bin/bash
# generates article-json from the contents of the `elife-article-xml` repo.
set -e

./install.sh
./download-elife-xml.sh

echo > scrape.log

# capture ctrl-c and call the `ctrl_c` fn
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

num="$1"

mkdir -p article-json

if [ ! -z "$num" ]; then
    time venv/bin/python src/generate_article_json.py --num "$num"
else
    time venv/bin/python src/generate_article_json.py
fi
