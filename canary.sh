#!/bin/bash

# everything must pass
set -e

# reload the virtualenv
rm -rf venv/
virtualenv --python=`which python2` venv
source venv/bin/activate
pip install -r requirements.txt

# upgrade all deps to latest version
pip install pip-review
pip-review --pre # preview the upgrades
echo "[any key to continue ...]"
read -p "$*"
pip-review --auto --pre # update everything

# run the tests
#python src/manage.py migrate
#./src/manage.py test src/
source update-api-raml.sh
./.test.sh
