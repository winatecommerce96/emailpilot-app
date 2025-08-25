#!/usr/bin/env bash
# Safe apply: prepend GPT‑5 policy to CLAUDE.md (creates backup); or --revert to restore
set -euo pipefail
if [ "${1:-}" = "--revert" ]; then
  latest=$(ls -1t CLAUDE.md.pre-gpt5.* 2>/dev/null | head -n1 || true)
  if [ -n "$latest" ]; then
    mv "$latest" CLAUDE.md
    echo "Restored CLAUDE.md from $latest"
  else
    echo "No backup found"; exit 1
  fi
  exit 0
fi
if [ ! -f CLAUDE.md ]; then
  echo "No CLAUDE.md to modify; aborting."; exit 1
fi
stamp="$(date +%Y%m%d-%H%M%S)"
cp CLAUDE.md "CLAUDE.md.pre-gpt5.$stamp"
{ head -n 1 CLAUDE.md | grep -q 'GPT‑5 Orchestration Policy' ; } && { echo "Already applied."; exit 0; } || true
cat CLAUDE_gpt5.md CLAUDE.md > CLAUDE.tmp && mv CLAUDE.tmp CLAUDE.md
echo "Applied GPT‑5 policy to CLAUDE.md (backup at CLAUDE.md.pre-gpt5.$stamp)"
