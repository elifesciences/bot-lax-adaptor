#!/bin/bash

set -e # everything must pass

# ensure the venv is installed
. ./install.sh &> /dev/null

# activate venv
. ./venv/bin/activate

# lint
. ./.lint.sh

# update the api-raml
. ./download-api-raml.sh

# test! finally!
. ./.test.sh
