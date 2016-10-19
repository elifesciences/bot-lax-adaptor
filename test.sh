#!/bin/bash

set -e # everything must pass

# ensure the venv is installed
. ./install.sh

# activate venv
. ./venv/bin/activate

# lint
. ./.lint.sh

# update the api-raml
. ./download-api-raml.sh

# validate the schema
. ./.validate-schema.sh

# test! finally!
. ./.test.sh
