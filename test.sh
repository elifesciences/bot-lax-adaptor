#!/bin/bash

set -e # everything must pass

# ensure the venv is installed
. ./install.sh &> /dev/null

# activate venv
. ./venv/bin/activate

# run tests
export PYTHONPATH="src"
args="$@"
module=""
if [ ! -z "$args" ]; then
    module=".$args"
fi
green src"$module"

coverage report

# run coverage test
# only report coverage if we're running a complete set of tests
if [ -z "$module" ]; then
    # is only run if tests pass
    covered=$(coverage report | grep TOTAL | awk '{print $6}' | sed 's/%//')
    if [ $covered -lt 90 ]; then
        echo
        echo "FAILED this project requires at least 90% coverage"
        echo
        exit 1
    fi
fi
