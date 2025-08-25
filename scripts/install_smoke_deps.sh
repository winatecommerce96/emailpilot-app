#!/usr/bin/env bash
set -euo pipefail
python -m pip install -q --upgrade pip
python -m pip install -q pytest requests ruff mypy
echo "✅ Python smoke/static deps installed."
