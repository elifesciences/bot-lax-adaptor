#!/bin/bash
# clones/updates the repository of elife's article xml
# this xml is used for bulk runs of the article-json generator
set -e # everything must pass

# REMOVE when all article-xml repositories are not shallow anymore
# or TURN ON if needed to reset the state
#rm -rf article-xml

if [ ! -d article-xml ]; then
    if [ -d /home/elife/elife-article-xml ]; then
        # local copy on elife-libraries Jenkins node for faster cloning
        git clone file:///home/elife/elife-article-xml article-xml
    else
        git clone https://github.com/elifesciences/elife-article-xml article-xml
    fi
fi

if [ -f elife-article-xml.sha1 ]; then
    cd article-xml
    git checkout "$(cat ../elife-article-xml.sha1)"
    cd ..
fi
