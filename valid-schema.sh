#!/bin/bash
set -e

function validate {
    path=$1
    python -c "import sys,json; json.load(open(sys.argv[1], 'r'))" $path
}

for fname in `ls schema/*.json`; do
    echo -n "testing $fname ..."
    validate "$fname" && echo "passed" || {
        exit 1
    }
done
