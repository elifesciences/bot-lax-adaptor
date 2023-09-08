#!/bin/bash
# scrapes *many* articles from XML on the filesystem.
# see `generate-article-json.sh` to scrape *all* articles from XML.
# see `scrape-article.sh` to scrape a *single* article from XML.

set -eu

# a plain text file with one filename per line. should look similar to:
# elife-09419-v2.xml
# elife-15192-v2.xml
# elife-16019-v1.xml

scrape_file=${1:-scrape.txt}
output_dir=${2:-.}
if [ ! -f "$scrape_file" ]; then
    echo "input file doesn't exist"
    exit 1
fi

if [ ! -d "$output_dir" ]; then
    echo "output directory doesn't exist"
    exit 1
fi

# we ingest from the latest on the master branch
project_dir=$(pwd) # bot-lax project, where this script lives
xmlrepodir="$project_dir/article-xml/articles"
(
    . download-elife-xml.sh
    cd "$xmlrepodir"
    # do this because 'download-elife-xml.sh' obeys article-xml repository pin
    git reset --hard
    git checkout master
    git pull
)

source venv/bin/activate

while IFS= read -r line; do 
    article="$xmlrepodir/$line"
    # skip whitespace
    if [[ -z "${line// }" ]]; then
        continue
    fi
    # skip missing files
    if [ ! -f "$article" ]; then
        echo "file not found: $article"
        continue
    fi
    python src/main.py "$article" > "$output_dir/$line.json"
done < "$scrape_file"
