#/bin/bash
function is_int() { return $(test "$@" -eq "$@" > /dev/null 2>&1); }
source venv/bin/activate # contains unbound vars
set -eu
msid=$1
if $(is_int "$msid"); then
    PYTHONPATH=src python -c "import glencoe; print('clearing',glencoe.glencoe_url($msid)); glencoe.clear_cache($msid)"
else
    echo "msid must be an integer"
    exit 1
fi
