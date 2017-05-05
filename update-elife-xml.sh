#!/bin/bash
set -e

./download-elife-xml.sh
bot_lax_adaptor=$(pwd)
cd article-xml
git fetch
git rev-parse origin/master > "${bot_lax_adaptor}/elife-article-xml.sha1"
cd -
./download-elife-xml.sh

