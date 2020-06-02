#!/bin/bash
set -e

./download-api-raml.sh

cd schema/api-raml/
git fetch
sha=$(git rev-parse origin/structured-abstract-compiled)
cd -

echo $sha > api-raml.sha1

./download-api-raml.sh
