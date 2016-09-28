#/bin/bash
# generates article-json from a random article in the elife-article-xml repo

set -e # everything must pass

if [ -d $PWD ]; then
    . download-elife-xml.sh &> /dev/null
fi

PWD=article-xml/articles/
random_file=$(ls $PWD | sort -R | tail -n 1)
python src/main.py "./$PWD$random_file"
