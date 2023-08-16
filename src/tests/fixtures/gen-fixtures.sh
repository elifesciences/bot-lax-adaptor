#!/bin/bash
set -xuv
home=$(pwd)
scraper="../../../"

function scrape {
    {
        cd "$scraper"
        for fname in "$@" # consume all/rest of args
        do
            for path in ./article-xml/articles/$fname*; do
                path=$(realpath "$path")
                nom=${path##*/} # basename, "elife-09560.xml"
                xmllint "$path" --format > "$home/$nom"
                ./scrape-article.sh "$path" > "$home/$nom.json"
           done
        done
    }
}

scrape elife-09560-v1 elife-16695-v1 elife-24271-v1 elife-36409-v2
