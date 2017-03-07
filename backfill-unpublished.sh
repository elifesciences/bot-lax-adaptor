#!/bin/bash
# invalid and unpublished articles will avoid a regular backfill because they 
# are absent from the github repo. when it comes time to publish them, they'll 
# fail.this state comes about when:
#
# 1. we allow invalid article-json on INGEST.
# this was the state for many months to ease the backpressure on production
#
# 2. we change what 'valid' means
# our schema may change on us and what was once valid no longer is.
# if there are unpublished articles in lax when this happens, they will fail to publish.

set -ev
/srv/lax/manage.sh status article-versions.invalid-unpublished.list | jq '.[][]' --compact-output | python src/backfill.py
