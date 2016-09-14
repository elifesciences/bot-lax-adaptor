#!/bin/bash
set -e
source download-api-raml.sh
echo > validate.log

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

passed=0
failed=0
for i in `ls ./article-json/*.json | sort`; do 
    echo "validating" $(basename $i)
    python ./src/validate.py $i >> validate.log 2>&1 && ((passed+=1)) || {
        echo "failed to validate $(basename $i)"
        ((failed+=1))
    }
done
echo "passed: $passed"
echo "failed: $failed"
