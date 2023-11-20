#!/bin/bash
set -e
source venv/bin/activate

if ! command -v ccache > /dev/null; then
    echo "ccache not found"
    exit 1
fi

# implicit exceptions disabled, not too helpful
# standalone disabled, we're compiling for testing, not for distribution

time nuitka3 \
    --main=src/main.py \
    --follow-imports \
    --warn-unusual-code \
    --nofollow-import-to='*.tests,boto,boto3,botocore'

test -f main.bin
