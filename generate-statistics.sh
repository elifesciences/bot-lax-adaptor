#!/bin/bash
# print statistics on the generation by checking its stdout
set -e

log=$1
generated_green=$(grep '^elife-[0-9]\+-v[0-9]\+\.xml ->' $log | grep success | wc -l)
generated_red=$(grep '^elife-[0-9]\+-v[0-9]\+\.xml ->' $log | grep -v success | wc -l)
generated_total=$(grep '^elife-[0-9]\+-v[0-9]\+\.xml ->' $log | wc -l)
input=$(ls -1 article-xml/articles/elife-* | wc -l)
echo "Input: ${input} XML articles"
echo "Generated green,red,total: ${generated_green},${generated_red},${generated_total}"
