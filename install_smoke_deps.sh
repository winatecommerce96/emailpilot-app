#!/usr/bin/env bash
# Corrected: install Python deps with pip; JS/TS tools with npm (if package.json exists)
set -euo pipefail

echo "🐍 Installing Python smoke/static deps (pytest, requests, ruff, mypy)…"
python -m pip install -q --upgrade pip
python -m pip install -q pytest requests ruff mypy

if [ -f package.json ]; then
  echo "🟩 package.json detected — ensuring Node/JS tools…"
  if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm is not installed. Install Node.js (e.g., 'brew install node' on macOS) and re-run." >&2
    exit 1
  fi
  # Install TypeScript & ESLint if not already present in devDependencies
  npx --yes --version >/dev/null 2>&1 || true
  TS_PRESENT=$(node -e "try{p=require('./package.json');console.log(p.devDependencies?.typescript?'yes':'no')}catch(e){console.log('no')}")
  ESLINT_PRESENT=$(node -e "try{p=require('./package.json');console.log(p.devDependencies?.eslint?'yes':'no')}catch(e){console.log('no')}")

  if [ "$TS_PRESENT" = "no" ]; then
    echo "Installing TypeScript locally (devDependency)…"
    npm i -D typescript >/dev/null
  fi
  if [ "$ESLINT_PRESENT" = "no" ]; then
    echo "Installing ESLint locally (devDependency)…"
    npm i -D eslint >/dev/null
  fi

  echo "Verifying toolchain…"
  npx -y tsc --version >/dev/null
  npx -y eslint --version >/dev/null || true
  echo "✅ JS/TS tools ready."
else
  echo "ℹ️ No package.json found — skipping JS/TS tools (tsc/eslint)."
fi

echo "✅ Smoke deps installed."
