#!/bin/bash
# generates and validate a small subset of articles that should always pass.
# ensures generated article-json is reproducible.

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
rm -f guinea-pigs/* guinea-pigs.log sums.md5
for article in $guinea_pigs; do
    echo "Guinea pig ${article}"
    ./scrape-article.sh article-xml/articles/$article > guinea-pigs/$article.json
    ./validate-json.sh guinea-pigs/$article.json >> guinea-pigs.log
done

md5sum guinea-pigs/*.json > sums.md5

for article in $guinea_pigs; do
    echo "Guinea pig (scrape two) ${article}"
    ./scrape-article.sh article-xml/articles/$article > guinea-pigs/$article.json
done

echo "hash check ..."
md5sum --check sums.md5 | tee --append guinea-pigs.log

echo "done!"
