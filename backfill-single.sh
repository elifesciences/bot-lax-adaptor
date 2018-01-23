#!/bin/bash
set -e

if [ "$#" != 3 ]; then
    echo "Usage: ./backfill-single.sh MSID VERSION PATH"
    echo "Example: ./backfill-single.sh 10627 1 article-xml/articles/elife-10627-v1.xml"
    exit 1
fi

# we ingest from the latest on the master branch
prjdir=$(pwd) # bot-lax project, where this script lives
xmlrepodir="$prjdir/article-xml/articles"
(
    . download-elife-xml.sh
    cd $xmlrepodir
    git reset --hard
    git checkout master
    git pull
)

msid="$1"
version="$2"
location="$3"

echo "{\"msid\":$msid, \"version\":$version, \"location\":\"$location\"}" | venv/bin/python src/adhoc_backfill.py
