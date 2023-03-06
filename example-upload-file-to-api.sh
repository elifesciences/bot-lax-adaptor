#!/bin/bash
# POSTs a given XML file to the /xml endpoint.
# it will be converted to article-json and validated.
set -e
id=9561
version=1
filename=article-xml/articles/elife-09561-v1.xml
if [ ! -f $filename ]; then
    echo "file not found: $filename"
    exit 1
fi
curl -v -F "xml=@$filename" "http://127.0.0.1:8080/xml?id=$id&version=$version"
