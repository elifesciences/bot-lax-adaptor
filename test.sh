#!/bin/bash

set -e # everything must pass

rm -rf venv/

. install.sh

. .lint.sh

. .validate-schema.sh

. .test.sh
