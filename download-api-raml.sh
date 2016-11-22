#!/bin/bash
# clones/updates the elife api-raml repository
# this repository contains the specification for article-json and
# is used to validate what the scraper generates.
# see `src/validate.py`

set -e # everything must pass
cd schema
if [ -d api-raml ]; then
    cd api-raml
    git reset --hard
    git fetch
    if [ -f elife-article-xml.sha1 ]; then
        git checkout $(cat elife-article-xml.sha1)
    else
        git checkout master
        git pull origin master
    fi
    cd ..
else
    git clone https://github.com/elifesciences/api-raml --depth 1
fi
cd ..
