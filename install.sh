#!/bin/bash
set -e # everything must succeed.
echo "[-] install.sh"

. download-api-raml.sh

. mkvenv.sh

source venv/bin/activate
pip install pip wheel --upgrade

# link the default (elife) config if no app.cfg file found
if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

if pip list | grep elifetools; then
    pip uninstall -y elifetools
fi

# temporary until connexion library fixes their requirements config
if pip list | grep connexion; then
    pip uninstall -y connexion
fi

# use legacy resolver until we can port to pipenv
pip install -r requirements.txt --use-deprecated=legacy-resolver

echo "[✓] install.sh"
