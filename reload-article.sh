#!/bin/bash

set -e
#set -xv

art=$1;

# where files will be loaded
tmpdir="$(pwd)/adhoc-$(date -I)"
mkdir -p "$tmpdir"

path="$tmpdir/$(basename $art).json"
echo "scraping to $path"

time ./scrape-article.sh "$art" > "$path"

echo "validating $path"
time ./validate-json.sh $path > /dev/null

# script will end here if invalid

echo "successfully scraped and validated"

lax="/srv/lax/"
action="ingest"
time "$lax/manage.sh" ingest "--$action" --force --dir "$tmpdir"
