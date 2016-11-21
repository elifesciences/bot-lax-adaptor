#!/bin/bash
# print statistics on the generation by checking its stdout
set -e

log=$1
validated_green=$(grep '^elife-[0-9]\+-v[0-9]\+\.xml\.json =>' $log | grep success | wc -l)
validated_red=$(grep '^elife-[0-9]\+-v[0-9]\+\.xml\.json =>' $log | grep -v success | wc -l)
input=$(ls -1 article-json/elife-* | wc -l)
echo "Input: ${input} JSON articles"
echo "Validated green,red: ${validated_green},${validated_red}"
