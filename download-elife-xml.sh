#!/bin/bash
# clones/updates the repository of elife's article xml
# this xml is used for bulk runs of the article-json generator
set -e # everything must pass
if [ -d article-xml ]; then
    cd article-xml
    git reset --hard
    git pull
    cd ..
elif [ -d /home/elife/elife-article-xml ]; then
    # local copy on elife-libraries Jenkins node for faster cloning
    git clone file:///home/elife/elife-article-xml article-xml
else
    git clone https://github.com/elifesciences/elife-article-xml article-xml
fi

if [ -f elife-article-xml.sha1 ]; then
    cd article-xml
    # existing elife-article-xml shallow clones, containing only 1 commit
    git fetch --depth 1000
    git checkout "$(cat ../elife-article-xml.sha1)"
    cd ..
fi
