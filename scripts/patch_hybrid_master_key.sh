#!/usr/bin/env bash
# scripts/patch_hybrid_master_key.sh
# Injects/updates master_key in config/gpt5/hybrid.yaml using .env:LITELLM_MASTER_KEY
set -euo pipefail
ROOT="${PROJECT_ROOT:-$(pwd)}"
CFG="${CFG_FILE:-$ROOT/config/gpt5/hybrid.yaml}"
ENV_FILE="$ROOT/.env"

[[ -f "$CFG" ]] || { echo "❌ Missing $CFG"; exit 1; }
[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }
: "${LITELLM_MASTER_KEY:?Set LITELLM_MASTER_KEY in .env or env}"

tmp="$(mktemp)"
awk -v key="$LITELLM_MASTER_KEY" '
  BEGIN { updated=0 }
  /^[[:space:]]*master_key:/ {
      print "  master_key: \"" key "\""
      updated=1
      next
  }
  { print }
  END {
      if (updated==0) {
          print ""
          print "general_settings:"
          print "  master_key: \"" key "\""
      }
  }
' "$CFG" > "$tmp"
mv "$tmp" "$CFG"
echo "✅ Updated master_key in $CFG"
grep -n "master_key:" "$CFG" | sed -n '1p'
