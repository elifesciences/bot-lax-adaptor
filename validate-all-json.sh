#!/bin/bash
# validates the article-json found in the `./article-json` directory.
# this directory is populated by the `generate-article-json.sh` script.

set -e

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

# clean up
rm -f linux-amd64
rm -f validation.log validate.log
rm -rf ./article-json/valid/ ./article-json/invalid/  ./article-json/patched/

# fetch latest validator
wget https://github.com/elifesciences/validate-article-json/releases/latest/download/linux-amd64
chmod +x linux-amd64
mv linux-amd64 validate-article-json

# validate
sample="-1"      # 'all' articles (do not sample)
num_workers="72" # 36 cores (elife-libraries--powerful3) * 2
time ./validate-article-json schema/api-raml/ article-json/ "$sample" "$num_workers"
