#!/bin/bash
# validates the article-json found in the `./article-json` directory.
# this directory is populated by the `generate-article-json.sh` script.

set -e # everything must pass

# zero out the validation log
# python writes to this file
echo > validate.log

. install.sh 2> /dev/null

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

rm -rf ./article-json/valid/ ./article-json/invalid/
mkdir ./article-json/valid/ ./article-json/invalid/

time python src/validate_article_json.py
