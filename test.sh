#!/bin/bash

set -e # everything must pass

. install.sh

. .lint.sh

. .validate-schema.sh

. .test.sh
