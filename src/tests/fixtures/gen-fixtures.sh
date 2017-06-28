#!/bin/bash
set -xuv
home=$(pwd)
scraper="../../../"

function scrape {
    cd $scraper
    fname_list="$@" # consume all/rest of args
    for fname in $fname_list
    do
       for path in ./article-xml/articles/$fname*
       do
         nom=${path##*/} # basename, ll: elife-09560.xml
         cp $path $home/$nom
         ./scrape-article.sh "$path" > "$home/$nom.json"
       done
    done
    cd -
}

scrape elife-00666-v1 elife-09560-v1 elife-16695-v1
