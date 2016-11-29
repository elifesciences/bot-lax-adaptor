#!/bin/bash
# copies the article-json found in the `./article-json/valid` directory 
# to a working copy of the elife-article-json repository.
set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: ${0} /tmp/elife-article-json"
    exit 1
fi

target_repository=$1
cp ./article-json/valid/*.json $target_repository/articles/
cd $target_repository
git diff --exit-code > /dev/null || {
    git add articles/
    modified_articles=$(git diff --cached --name-status | wc -l)
    git commit -m "Added or modified $modified_articles articles"
}
cd -
