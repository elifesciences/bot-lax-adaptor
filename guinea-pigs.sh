#!/bin/bash
# generates a validate a small subset of articles that should always pass

set -e

guinea_pigs="
elife-00230-v1.xml
elife-00625-v1.xml
elife-00790-v1.xml
elife-01222-v1.xml
elife-01239-v1.xml
elife-03318-v1.xml
elife-04177-v2.xml
elife-04637-v1.xml
elife-04970-v2.xml
elife-06213-v3.xml
elife-08245-v1.xml
elife-10635-v2.xml
elife-15600-v1.xml
elife-15853-v1.xml
elife-15893-v1.xml
"

mkdir -p guinea-pigs
rm -f guinea-pigs/* guinea-pigs.log
for article in $guinea_pigs; do
    echo "Guinea pig ${article}"
    ./scrape-article.sh article-xml/articles/$article >> guinea-pigs/$article.json
    ./validate-json.sh guinea-pigs/$article.json >> guinea-pigs.log
done
