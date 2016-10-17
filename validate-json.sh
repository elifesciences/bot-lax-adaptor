#!/bin/bash
# validates the article-json found in the `./article-json` directory.
# this directory is populated by the `generate-article-json.sh` script.

set -e # everything must pass
. download-api-raml.sh
echo > validate.log

. install.sh 2> /dev/null

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

rm -rf ./article-json/valid/ ./article-json/invalid/
mkdir ./article-json/valid/ ./article-json/invalid/

passed=0
failed=0

for i in `ls ./article-json/*.json | sort`; do 
    fname=$(basename $i)
    python ./src/validate.py $i && \
    ((passed+=1)) && \
    ln -s "../$fname" "./article-json/valid/$fname" || {
        ((failed+=1)) && \
        ln -s "../$fname" "./article-json/invalid/$fname"
    }
done

echo "valid json can be found in ./article-json/valid/"
echo "invalid json can be found in ./article-json/invalid/"
echo "passed: $passed"
echo "failed: $failed"
echo "$passed/$failed" > validation-results.txt
