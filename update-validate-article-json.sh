#!/bin/bash
# fetch latest validate-article-json
set -e

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

if [ ! -e validate-article-json ]; then
    wget "https://github.com/elifesciences/validate-article-json/releases/latest/download/$fname" \
        --quiet \
        --output-document=validate-article-json
    chmod +x validate-article-json
else 
    printf "checking ... "
    wget "https://github.com/elifesciences/validate-article-json/releases/latest/download/$fname.sha256" \
        --quiet \
        --output-document=validate-article-json.sha256
    sed -ie 's/linux-amd64/validate-article-json/' validate-article-json.sha256
    sha256sum --check validate-article-json.sha256 || {
        printf "updating validate-article-json ... "
        rm -f validate-article-json
        wget "https://github.com/elifesciences/validate-article-json/releases/latest/download/$fname" \
            --quiet \
            --output-document=validate-article-json
        chmod +x validate-article-json
        printf "done\n"
    }

fi
