#!/bin/bash
set -e

./download-elife-xml.sh
cd article-xml
git fetch
git rev-parse origin/master > ../elife-article-xml.sha1
cd -
./download-elife-xml.sh

