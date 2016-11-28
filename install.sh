#!/bin/bash
set -e

if [ ! -d venv ]; then
    # build venv if one doesn't exist
    virtualenv --python=`which python2` venv
fi

source venv/bin/activate

pip uninstall -y elifetools
pip install -r requirements.txt

. download-api-raml.sh
