#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -q -U pip
.venv/bin/pip install -q -r requirements-local.txt
echo "ok: .venv ready (python $(.venv/bin/python -V 2>&1))"
