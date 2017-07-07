#!/bin/bash
set -e

echo "[-] .lint.sh"

export PYTHONPATH="src/"

# remove any old compiled python files
# pylint likes to lint them
find src/ -name '*.py[c|~]' -delete
find src/ -regex "\(.*__pycache__.*\|*.py[co]\)" -delete

echo "pyflakes"
pyflakes ./src/

echo "pylint"
pylint -E src/* --disable=unbalanced-tuple-unpacking 2> /dev/null

echo "scrubbing"
. .scrub.sh 2> /dev/null

echo "[✓] .lint.sh"
