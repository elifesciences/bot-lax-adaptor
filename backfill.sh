#!/bin/bash
set -e
source venv/bin/activate

# pseudo code

# this is where articles will be downloaded/linked to for backfill
runpath="run-$(date "%Y%m%d%H%M%S)"
mkdir "$runpath"
cd "$runpath"

# iterate over response from lax about the articles it knows about
# (should be *all* articles, lax is now the publishing authority)
for msid, version, ispublished, remotepath in $(/srv/lax/manage.sh report all-article-versions)
do
    xmlpath="./article-xml/articles/elife-$msid-v$version.xml"
    if [ -e $xmlpath ]; then
        # xml exists, symlink it in
        ln -sfT $xmlpath
    else
        wget $remotepath
    fi
end;


# generate article-json
time python src/generate_article_json.py $runpath

# validate it all
time python src/validate_article_json.py $runpath

lax="/srv/lax/"

# call the lax 'ingest' command with a directory of valid article json
time "$lax/manage.sh" ingest "$action" --force --dir "$runpath"
