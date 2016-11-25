#!/bin/bash
set -e

host=${1-end2end--journal.elifesciences.org}

source venv/bin/activate
rm -f load_all_urls.log
python urls.py article-json/ | sort | uniq | xargs -n 1 -I '{}' -P 4 curl -v https://$host'{}' -s -o /dev/null -w "{},%{http_code}\n" | tee -a load_all_urls.log
