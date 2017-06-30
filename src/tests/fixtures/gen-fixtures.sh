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
            if [ "$nom" = "elife-00666-v1.xml" ]; then
                # download the kitchen sink.
                wget https://raw.githubusercontent.com/elifesciences/XML-mapping/master/elife-00666.xml -O /tmp/elife-00666.xml
                cat /tmp/elife-00666.xml | xmllint --format - > "$home/$nom"
                cp "$home/$nom" "$home/$nom.invalid" # you'll have to make invalid again (just remove the title)
                path="$home/$nom"
            else
                cat $path | xmllint --format - > "$home/$nom"
            fi
            ./scrape-article.sh $path > "$home/$nom.json"
       done
    done
    cd -
}

scrape elife-00666-v1 elife-09560-v1 elife-16695-v1
