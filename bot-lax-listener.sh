#!/bin/bash

set -e

. install.sh
exec ./.bot-lax-listener.sh $1
