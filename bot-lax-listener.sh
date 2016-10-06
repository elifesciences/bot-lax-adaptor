#!/bin/bash

set -e

# the 'ci' in 'lax--ci'
instance_id=$1

. install.sh

python src/adaptor.py --type sqs --instance "$instance_id"
