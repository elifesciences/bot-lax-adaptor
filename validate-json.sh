#!/bin/bash
set -e
source download-api-raml.sh
echo > validate.log

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

for i in `ls ./article-json/*.json | sort -r`; do 
    echo "validating" $(basename $i)
    python ./src/validate.py $i
done
