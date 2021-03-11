#!/bin/bash
# backills *many* articles from XML on the filesystem.
# see `backfill.sh` to backfill *all* articles from XML.
# see `backfill-single.sh` to backfill a *single* article from XML.

set -eu

backfill_file=${1:-backfill.txt}

# we ingest from the latest on the master branch
prjdir=$(pwd) # bot-lax project, where this script lives
xmlrepodir="$prjdir/article-xml/articles"
(
    . download-elife-xml.sh
    cd "$xmlrepodir"
    # do this because 'download-elife-xml.sh' obeys article-xml repository pin
    git reset --hard
    git checkout master
    git pull
)

source venv/bin/activate

python ./src/backfill-many.py --xml-repo-dir "$xmlrepodir" --backfill-file "$backfill_file"
