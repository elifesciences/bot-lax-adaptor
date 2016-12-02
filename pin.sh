#!/bin/bash
set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /srv/lax/bot-lax-adaptor.sha1"
fi

sha1_file=$1
if test -e $sha1_file; then
    sha1=$(cat $sha1_file)
    git checkout $sha1
else
    echo "${sha1_file} not found, nothing to do"
fi
