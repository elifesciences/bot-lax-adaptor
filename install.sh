#!/bin/bash
set -e

if [ ! -d venv ]; then
    # build venv if one doesn't exist
    virtualenv --python=`which python2` venv
fi

source venv/bin/activate
pip install -r requirements.txt
pip install git+https://github.com/elifesciences/elife-tools.git@develop#egg=elifetools --upgrade
