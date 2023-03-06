#!/bin/bash
set -e

export PYTHONPATH="src/"

# remove any old compiled python files
# pylint likes to lint them
find src/ -name '*.py[c|~]' -delete
find src/ -regex "\(.*__pycache__.*\|*.py[co]\)" -delete

echo "pyflakes"
pyflakes ./src/

echo "pylint"
pylint -E src/*
# specific warnings we're interested in, comma separated with no spaces
# presence of these warnings are a failure
pylint ./src/* --disable=all --reports=n --score=n \
    --enable=redefined-builtin

echo "scrubbing"
. .scrub.sh
