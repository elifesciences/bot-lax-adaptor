#!/bin/bash

set -e # everything must pass

# ensure the venv is installed
. install.sh

# activate venv
. venv/bin/activate

# lint
. .lint.sh

# validate the schema
. .validate-schema.sh

# test! finally!
. .test.sh
