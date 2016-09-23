#!/bin/bash
set -e

export PYTHONPATH="src/"

echo "* calling pyflakes"
# if grep has output, fail
pyflakes src/

echo "* calling pylint"
pylint -E src/* 2> /dev/null

echo "* passed linting"
