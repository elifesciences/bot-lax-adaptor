#!/bin/bash

set -e

source venv/bin/activate
exec ./.bot-lax-listener.sh
