#!/bin/bash
# this script is used to update the article-json stored in lax
# performing just an INGEST of content, *no* PUBLISH events are
# sent whatsoever.

# talking to lax via the adaptor.py script for many thousands of articles is
# extremely slow, so this script bypasses all that, bulk generates articles,
# bulk validates them then tells lax to do a bulk ingest.

set -euo pipefail # strict mode
#set -xv # debugging

# housekeeping

type realpath &> /dev/null || { 
    echo '"realpath" is required'
    exit 1
}

trap ctrl_c INT
function ctrl_c() {
    echo "caught ctrl-c"
    exit 1
}

srcdir=$(pwd)
errcho(){ >&2 echo $@; }

# where articles will be linked to/downloaded for backfill
defaultrunpath="run-$(date +'%Y%m%d%H%M%S')"
runpath=${1:-$defaultrunpath}
runpath=$(realpath $runpath)
mkdir -p "$runpath"

if [ ! -z "$@" ]; then
    # args were provided to backfill.sh
    shift # download-api-raml.sh also takes an arg
fi

# confirm

echo "backfill.sh

this script will:
1. pull latest article-xml from elifesciences/elife-article-xml (large repo)
2. download any missing/unpublished articles after consulting Lax (needs /srv/lax, s3 auth)
3. create a 'backfill-run' directory with symbolic links to the xml to be processed
4. generate article-json from ALL xml in the ./articles-xml/articles/ directory (long process)
5. validate all generated article-json, failing if any are invalid
6. force an INGEST into Lax for all valid articles (needs /srv/lax)"

read -p "any key to continue (ctrl-c to quit) "

# begin

. download-elife-xml.sh

# activate venv
set +o nounset; . install.sh; set -o nounset; # virtualenv has unset vars we can't control

# where to find xml on the fs
xmlrepodir="$srcdir/article-xml/articles"

# where to download unpublished xml to
unpubxmldir="$srcdir/unpub-article-xml"
mkdir -p "$unpubxmldir" # (create if necessary)

# where generated article-json will be stored
ajsondir="$runpath/ajson"
mkdir -p "$ajsondir"

# where the results of validation will be stored
validdir="$ajsondir/valid"
invaliddir="$ajsondir/invalid"

# because we can choose an existing directory for the run
# ensure the results of any previous run are empty
rm -rf "$validdir" "$invaliddir"
mkdir "$validdir" "$invaliddir"


#
#
#

# switch to the run dir
cd "$runpath"

# iterate over response from lax about the articles it knows about
# (should be *all* articles, lax is now the publishing authority)
# https://www.cyberciti.biz/faq/unix-linux-bash-read-comma-separated-cvsfile/
OLDIFS=$IFS
IFS=,

errcho "fetching articles from lax"
/srv/lax/manage.sh --skip-install report all-article-versions-as-csv | while read msid version remotepath
do
    # ll: elife-00003-v1.xml
    fname="elife-$msid-v$version.xml" 

    # ll: /home/user/bot-lax/article-xml/articles/elife-00003-v1.xml
    xmlpath="$xmlrepodir/$fname"
    
    # ll: /home/user/bot-lax/unpub-article-xml/elife-00003-v1.xml
    xmlunpubpath="$unpubxmldir/$fname"
    
    # we look in both places for xml and if it's in neither, we download it

    if [ ! -f $xmlpath ] && [ ! -f $xmlunpubpath ]; then
        # lax doesn't know where the remote location and it's not on the fs
        if [ $remotepath = "no-location-stored" ]; then
            errcho "$fname not found, skipping"
            continue
        fi

        # xml absent, download it
        # download.py reuses code in the adaptor and does an authenticated requests to s3
        python $srcdir/src/download.py "$remotepath" "$xmlunpubpath"
    fi

    #errcho "linking $fname"

    # link it in to the run dir
    if [ -f $xmlpath ]; then
        ln -sfT $xmlpath $fname
    else
        ln -sfT $xmlunpubpath $fname
    fi
done
IFS=$OLDIFS

# switch back to bot-lax dir
cd -

# generate article-json 
# generated files are stored in $ajsondir
echo > "$srcdir/scrape.log"
time python src/generate_article_json.py "$runpath" "$ajsondir"

# validate all generated article-json
echo > "$srcdir/validate.log"
time python src/validate_article_json.py "$ajsondir"

# call the lax 'ingest' command with a directory of valid article json
time /srv/lax/manage.sh --skip-install ingest --ingest --force --dir "$validdir"

# clean up
# rm unpubdir/*; rmdir unpubdir
# rm rundir/*; rmdir rundir
