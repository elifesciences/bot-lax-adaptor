#!/bin/bash
# helps development of both scraper and elife-tools together
set -e
if [ ! -d elife-tools ]; then
    git clone ssh://git@github.com/elifesciences/elife-tools
fi
cd src
ln -sfn ../elife-tools/elifetools
cd ..
. ./install.sh
pip uninstall elife-tools || true
pip install -r elife-tools/requirements.txt
