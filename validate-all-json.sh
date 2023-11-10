#!/bin/bash
# validates the article-json found in the `./article-json` directory.
# this directory is populated by the `generate-article-json.sh` script.

set -ex

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT
function ctrl_c() {
    exit 1
}

# clean up
rm -f linux-amd64 linux-arm64 validate-article-json
rm -f validation.log validate.log
rm -rf ./article-json/valid/ ./article-json/invalid/  ./article-json/patched/

# fetch latest validator
arch=$(uname -m)
fname=""
if [ "$arch" = "x86_64" ]; then
    fname="linux-amd64"
fi

# aka "ARM64"
if [ "$arch" = "aarch64" ]; then
    fname="linux-arm64"
fi

if [ -z "$fname" ]; then
    echo "unsupported architecture: $arch"
    exit 1
fi

wget "https://github.com/elifesciences/validate-article-json/releases/latest/download/$fname" \
    --quiet \
    --output-document=validate-article-json
chmod +x validate-article-json

# validate
sample="-1"      # 'all' articles (do not sample)
num_workers="-1" # '-1' is unbounded
buffer_size="5000" # ~7.5GiB RAM
time ./validate-article-json schema/api-raml/ article-json/ "$sample" "$num_workers" "$buffer_size"
