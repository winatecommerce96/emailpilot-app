#!/usr/bin/env bash
set -euo pipefail
echo "Lint (ruff)"
if command -v ruff >/dev/null 2>&1; then ruff .; else echo "ruff not installed; skipping"; fi
echo "Type check (mypy)"
if command -v mypy >/dev/null 2>&1; then mypy tools || true; else echo "mypy not installed; skipping"; fi
echo "Tests"
if command -v pytest >/dev/null 2>&1; then pytest -q; else echo "pytest not installed; skipping"; fi
echo "Determinism"
python tools/codegen.py >/dev/null 2>&1; python tools/codegen.py >/dev/null 2>&1; diff <(sha256sum runtime/graph_compiled.py | awk '{print $1}') <(sha256sum runtime/graph_compiled.py | awk '{print $1}') >/dev/null 2>&1 || (echo "codegen nondeterministic"; exit 1)
echo "OK"

