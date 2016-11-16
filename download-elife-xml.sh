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
    git clone file:///home/elife/elife-article-xml article-xml --depth 1
else
    git clone https://github.com/elifesciences/elife-article-xml article-xml --depth 1
fi
