#!/bin/bash
set -e

if [ ! -d venv ]; then
    # build venv if one doesn't exist
    virtualenv --python=`which python2` venv
fi

source venv/bin/activate

# link the default (elife) config if no app.cfg file found
if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

if pip list | grep elifetools; then
    pip uninstall -y elifetools
fi
pip install -r requirements.txt

. download-api-raml.sh

cd schema/api-raml
npm install
node compile.js
cd -
