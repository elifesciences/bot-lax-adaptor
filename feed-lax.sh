#!/bin/bash
# feeds articles in the `./article-xml` directory into lax
set -e # everything must pass
. ./install.sh
. ./venv/bin/activate
. ./download-elife-xml.sh

args="$@"

python src/adapt.py $args
