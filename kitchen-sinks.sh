#!/bin/bash
# generates and validate the kitchen sinks

set -e

kitchen_sinks="
elife-00666-v1.xml
"

mkdir -p kitchen-sinks
rm -f kitchen-sinks/* kitchen-sinks.log
for article in $kitchen_sinks; do
    echo "Kitchen sink ${article}"
    ./scrape-article.sh src/tests/fixtures/$article > kitchen-sinks/$article.json
    ./validate-json.sh kitchen-sinks/$article.json >> kitchen-sinks.log
done

