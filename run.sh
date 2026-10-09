#!/bin/sh
# Create the venv if needed, install requirements, build assets, run the game.
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python tools/build_assets.py
exec .venv/bin/python main.py "$@"
