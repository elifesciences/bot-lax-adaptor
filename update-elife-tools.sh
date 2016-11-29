#!/bin/bash
set -e

rm -rf /tmp/elife-tools-shallow-clone
git clone --depth 1 https://github.com/elifesciences/elife-tools.git /tmp/elife-tools-shallow-clone
cd /tmp/elife-tools-shallow-clone
# this uses the develop branch, which is the default being cloned
elife_tools_sha1=$(git rev-parse HEAD)
cd -
sed -i -e "s;.*/elife-tools.git.*;git+https://github.com/elifesciences/elife-tools.git@${elife_tools_sha1}#egg=elifetools;g" requirements.txt
source venv/bin/activate
pip uninstall -y elifetools
pip install -r requirements.txt

