#!/bin/bash
# removes all expired entries from the requests cache root
set -e
source venv/bin/activate

# clear expired entries
output_path=$(cd src && python -c 'import http; print(http.clear_expired())')
