#!/bin/sh
set -e
apt-get update -qq
apt-get install -y -qq lua5.1 lua-cjson >/tmp/lua-install.log
python3 /app/router/tests/check_inventory.py
