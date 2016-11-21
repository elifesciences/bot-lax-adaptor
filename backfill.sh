#!/bin/bash
# the purpose of the bot-lax-adaptor project is to do the necessary data 
# wrangling of article data from the bot before sending it to lax. 
# this takes several forms:
# * listening to a queue for messages about which articles to process
# * processing directories of article xml from the filesystem
#
# this script is used to update the article-json stored in lax, performing just
# the ingestion of content - *no* PUBLISH events whatsoever.
#
# when pubdates need to be changed they must be issued as SILENT CORRECTIONS
# from the production workflow.

set -euo pipefail # strict mode

default_dir="$(pwd)/articles-xml/articles/"
dir=${1:-$default_dir}

trap ctrl_c INT
function ctrl_c() {
    echo "caught ctrl-c"
    exit 1
}

echo "backfill.sh

this script will:
1. pull latest article-xml from elifesciences/elife-article-xml
2. generate article-json from ALL xml in the ./articles-xml/articles/ directory
3. validate all article-json in the ./article-json/ directory
4. force an INGEST for all articles in the ./article-json/valid/ directory"

read -p "any key to continue (ctrl-c to quit) "

# import which dir of xmL?
if [ ! -z "$dir" ]; then
    # no dir passed through, assume default and update elife xml
    . download-elife-xml.sh
fi

# activate venv
set +o nounset; . install.sh; set -o nounset;

# this approach DOES NOT WORK WELL. v.slow
# python ./src/adaptor.py --action ingest --force --type fs #--dir "$1"

# instead, do this in bulk lots: download, bulk generate, bulk ingest 
# and skip the adaptor that handles different types of communication

. generate-article-json.sh
. validate-all-json.sh

lax="/home/luke/dev/python/lax" # obviously, we need to auto-detect this or fail here

# call the lax 'ingest' command with a directory of valid article json
time "$lax/manage.sh" ingest --ingest --force --dir "$(pwd)/article-json/valid/"


