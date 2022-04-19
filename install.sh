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

pip install -r requirements.txt

echo "[✓] install.sh"
