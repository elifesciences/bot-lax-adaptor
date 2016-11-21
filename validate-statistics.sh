#!/bin/bash
# print statistics on the generation by checking its stdout
set -e

log=$1
article_pattern='^elife-[0-9]\+-v[0-9]\+\.xml\.json =>'

validated_green=$(grep "$article_pattern" "$log" | grep success | wc -l)
validated_red=$(grep "$article_pattern" "$log" | grep -v success | wc -l)
validated_total=$(grep "$article_pattern" "$log" | wc -l)
input=$(ls -1 article-json/elife-* | wc -l)
echo "Input: ${input} JSON articles"
echo "Validated green,red: ${validated_green},${validated_red},${validated_total}"
