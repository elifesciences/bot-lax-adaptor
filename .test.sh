#!/bin/bash

set -e

export PYTHONPATH="src"

pyflakes src/

args="$*"
pytest "$args" \
    -vvv \
    --cov=src \
    --cov-report=

# only report coverage if we're running a complete set of tests.
if [ -z "$args" ]; then
    echo
    coverage report --fail-under 82
    echo
fi
