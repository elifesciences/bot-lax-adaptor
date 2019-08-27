#!/bin/bash
# removes all expired entries from the requests_cache db, shrinks db
set -e
source venv/bin/activate

# clear expired entries
output_path=$(cd src && python -c 'import cache_requests; print(cache_requests.clear_expired())')

# call VACUUM on the sqlite db to shrink it
du -sh "$output_path"
sqlite3 "$output_path" -line "VACUUM"
du -sh "$output_path"
