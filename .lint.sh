#!/bin/bash
set -e

# remove any old compiled python files
# pylint likes to lint them
find src/ -name '*.pyc' -delete

echo "* calling pyflakes"
pyflakes ./src/
echo "* calling pylint"
pylint -E ./src/** 2> /dev/null
echo "* passed linting"
