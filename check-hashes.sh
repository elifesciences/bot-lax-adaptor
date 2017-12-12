#!/bin/bash
# generates a hash for every file in $dir
# if hash exists and is different, exit out

# the intent of this script is that it's run between two corpus generations
# the first run will generate the article-json files, then the sumfile
# the second run will generate the article-json files again, then discover the
# sum file exists from previous run and use that to check no differences exist

set -e
set -xv

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

sumfile="sums.md5"

rm -rf article-json/ article-json-1/ article-json-2
mkdir -p article-json

python src/generate_article_json.py --num 100
md5sum article-json/*.json > article-json/$sumfile

cp -R article-json article-json-1

python src/generate_article_json.py --num 100
md5sum --check article-json/$sumfile || true

mv article-json article-json-2
