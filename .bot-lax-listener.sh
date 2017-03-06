#!/bin/bash
set -e

source venv/bin/activate

# the 'ci' in 'lax--ci'
instance_id=$1

exec python src/adaptor.py --type sqs
