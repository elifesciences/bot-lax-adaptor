#!/bin/bash
set -e

. venv/bin/activate

set -xv # debug

# housekeeping
thisdir=$(pwd)
errcho(){ >&2 echo $@; }

# where to find xml on the fs
xmlrepodir="$thisdir/article-xml/articles"

# where to download unpublished xml to
unpubxmldir="$thisdir/unpub-article-xml"
mkdir -p "$unpubxmldir" # (create if necessary)

# where articles will be linked to/downloaded for backfill
runpath="backfill-run-$(date +'%Y%m%d%H%M%S')"
mkdir "$runpath"

# where generated article-json will be stored
ajsondir="$runpath/ajson"
mkdir "$ajsondir"

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
/srv/lax/manage.sh --skip-install report all-article-versions-as-csv | while read msid version remotepath
do

    # ll: elife-00003-v1.xml
    fname="elife-$msid-v$version.xml" 

    if [ $remotepath = "no-location-stored" ]; then
        errcho "OMG - NO LOCATION FOR $fname"
        continue
    fi

    # ll: /home/user/bot-lax/article-xml/articles/elife-00003-v1.xml
    xmlpath="$xmlrepodir/$fname"
    
    # ll: /home/user/bot-lax/unpub-article-xml/elife-00003-v1.xml
    xmlunpubpath="$unpubxmldir/$fname"
    
    # we look in both places for xml and if it's in neither, we download it

    if [ ! -f $xmlpath ] && [ ! -f $xmlunpubpath ]; then
        # xml absent, download it
        # download.py reuses code in the adaptor and does an authenticated requests to s3
        python $thisdir/src/download.py "$remotepath" "$xmlunpubpath"
    fi

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
# generated files are stored in $runpath/ajson/
time python src/generate_article_json.py "$runpath"

exit

# validate all generated article-json
time python src/validate_article_json.py "$runpath"

lax="/srv/lax/"

# call the lax 'ingest' command with a directory of valid article json
time "$lax/manage.sh" ingest "$action" --force --dir "$runpath"

# clean up
# rm unpubdir/*; rmdir unpubdir
# rm rundir/*; rmdir rundir
