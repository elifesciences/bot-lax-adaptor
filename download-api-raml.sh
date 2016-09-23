#!/bin/bash
set -e
cd schema
if [ -d api-raml ]; then
    cd api-raml
    git reset --hard
    git pull
    cd ..
else
    git clone https://github.com/elifesciences/api-raml --depth 1
fi
cd ..
