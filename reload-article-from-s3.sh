#!/bin/bash
set -eu

# https://s3-external-1.amazonaws.com/bucket/path/to/elife-59976-v2.xml"
target=$1

# `--type s3` how to resolve `target`. can also handle the filesystem and AWS SQS
# `--action ingest+publish` does an ingest and the a publish in one action
# `--force` ignore publication status
# `--validate-only` do a 'dry run' and do not commit the transaction
python src/adaptor.py \
    --type s3 \
    --target "$target" \
    --action ingest+publish \
    --force \
    --validate-only
