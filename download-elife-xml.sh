#!/bin/bash
set -e
if [ -d article-xml ]; then
    cd article-xml
    git reset --hard
    git pull
    cd ..
else
    git clone https://github.com/elifesciences/elife-article-xml article-xml --depth 1
fi
