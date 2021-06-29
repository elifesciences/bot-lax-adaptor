#!/bin/bash
set -e

. install.sh 1>&2

rm -rf /tmp/elife-tools-shallow-clone
git clone --depth 1 https://github.com/elifesciences/elife-tools.git /tmp/elife-tools-shallow-clone
cd /tmp/elife-tools-shallow-clone
# this uses the develop branch, which is the default being cloned
elife_tools_sha1=$(git rev-parse HEAD)
cd - 1>&2
sed -i -e "s;.*/elife-tools.git.*;git+https://github.com/elifesciences/elife-tools.git@${elife_tools_sha1}#egg=elifetools;g" requirements.txt
pip uninstall -y elifetools 1>&2
pip install -r requirements.txt --use-deprecated=legacy-resolver 1>&2
echo "requirements.txt pinned to $elife_tools_sha1"
