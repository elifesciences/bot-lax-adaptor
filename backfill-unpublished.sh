#!/bin/bash
set -e
python src/backfill.py < /srv/lax/manage.sh status article-versions.invalid-unpublished.list
