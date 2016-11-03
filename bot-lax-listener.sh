#!/bin/bash

set -e

. install.sh

# the 'ci' in 'lax--ci'
instance_id=$1

exec python src/adaptor.py --type sqs --instance "$instance_id"
