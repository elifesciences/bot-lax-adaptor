#!/bin/bash
# print statistics on the validation by checking its stdout
set -e

log=$1
maximum_invalid=38
article_pattern='\- elife-[0-9]\+-v[0-9]\+\.xml\.json =>'

validated_green=$(grep "$article_pattern" "$log" | grep success | wc -l)
validated_red=$(grep "$article_pattern" "$log" | grep -v success | wc -l)
validated_total=$(grep "$article_pattern" "$log" | wc -l)
input=$(ls -1 article-json/elife-*.json | wc -l)
output_valid=$(ls -1 article-json/valid/elife-*.json | wc -l)
output_invalid=$(ls -1 article-json/invalid/elife-*.json | wc -l)
echo "Input: ${input} JSON articles"
echo "Output valid: ${output_valid} JSON articles"
echo "Output invalid: ${output_invalid} JSON articles"
echo "Validated green,red,total: ${validated_green},${validated_red},${validated_total}"

if [ ! "$validated_total" -eq "$input" ]; then
    echo "Input and total validates articles don't match"
    exit 2
fi

if [ ! "$validated_green" -eq "$output_valid" ]; then
    echo "Validated green and output valid articles don't match"
    exit 3
fi

if [ ! "$validated_red" -eq "$output_invalid" ]; then
    echo "Validated green and output valid articles don't match"
    exit 4
fi

if [ "$validated_red" -gt "$maximum_invalid" ]; then
    echo "No more than $maximum_invalid articles should be failing validation (with placeholders)"
    grep "${article_pattern}" "$log" | grep -v success
    exit 5
fi

