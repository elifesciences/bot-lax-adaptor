#!/bin/bash
# print statistics on the generation by checking its stdout
set -e

log=$1
article_pattern='^elife-[0-9]\+-v[0-9]\+\.xml ->'

generated_green=$(grep "$article_pattern" "$log" | grep success | wc -l)
generated_red=$(grep "$article_pattern" "$log" | grep -v success | wc -l)
generated_total=$(grep "$article_pattern" "$log" | wc -l)
input=$(ls -1 article-xml/articles/elife-* | wc -l)
echo "Input: ${input} XML articles"
echo "Generated green,red,total: ${generated_green},${generated_red},${generated_total}"

if [ ! "$generated_total" -eq "$input" ]; then
    echo "Input and total generated articles don't match"
    exit 2
fi

if [ "$generated_red" -gt 0 ]; then
    echo "No articles should be failing generation"
    grep "${article_pattern}" "$log" | grep -v success
    exit $generated_red
fi
