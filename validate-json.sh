#!/bin/bash
# validates the article-json found in the `./article-json` directory.
# this directory is populated by the `generate-article-json.sh` script.

set -e # everything must pass

filename=$1

# zero out the validation log
# python writes to this file
echo > validate.log

. install.sh

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

mkdir -p ./article-json/valid/ ./article-json/invalid/

time python src/validate.py "$filename"
