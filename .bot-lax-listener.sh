#!/bin/bash
set -e

source venv/bin/activate

exec python src/adaptor.py --type sqs
