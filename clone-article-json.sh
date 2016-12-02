#!/bin/bash
set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: ${0} /tmp/elife-article-json"
    exit 1
fi

folder=$1
if test -d $folder; then
    cd $folder
    git pull
    cd -
else
    git clone git@github.com:elifesciences/elife-article-json $folder
fi
