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
        git clone --origin cached-copy file:///home/elife/elife-article-xml article-xml
        cd article-xml
        git remote add origin https://github.com/elifesciences/elife-article-xml
        cd -
    else
        # article-xml respository doesn't exist, create it
        git clone https://github.com/elifesciences/elife-article-xml article-xml
    fi
fi

if [ -f elife-article-xml.sha1 ]; then
    bot_lax_adaptor=$(pwd)
    cd article-xml
    git fetch origin
    git checkout "$(cat "${bot_lax_adaptor}/elife-article-xml.sha1")"
    cd ..
fi
