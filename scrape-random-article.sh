#/bin/bash
set -e # everything must pass

PWD=article-xml/articles/
random_file=$(ls $PWD | sort -R | tail -n 1)
python src/main.py "./$PWD$random_file"
