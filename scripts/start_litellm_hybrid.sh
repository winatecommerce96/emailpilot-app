#!/usr/bin/env bash
# scripts/start_litellm_hybrid.sh — Minimal multi-provider launcher (OpenAI + Anthropic)
# Terminal A: run this to start LiteLLM with the hybrid config
set -euo pipefail
ROOT="${PROJECT_ROOT:-$(pwd)}"
CFG="${CFG_FILE:-$ROOT/config/gpt5/hybrid.yaml}"
VENV="$ROOT/.gpt5-hybrid"
HOST="127.0.0.1"
PORT="${PORT:-4000}"
ENV_FILE="$ROOT/.env"

# Load .env if present (to pick up keys)
[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }

: "${OPENAI_API_KEY:?Set OPENAI_API_KEY in .env or env}"
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY in .env or env}"

if [[ ! -f "$CFG" ]]; then
  echo "❌ Missing config: $CFG"
  echo "   Place hybrid.yaml at config/gpt5/hybrid.yaml"
  exit 1
fi

# Kill any stale process on the port
lsof -ti tcp:$PORT 2>/dev/null | xargs -r kill -9 || true

python3 -m venv "$VENV" 2>/dev/null || true
# shellcheck disable=SC1091
source "$VENV/bin/activate"

# Pin a known-good version; fall back to latest if pin fails
pip -q install -U pip || true
pip -q install "litellm[proxy]==1.43.5" || pip -q install "litellm[proxy]"

echo "🚀 LiteLLM → http://$HOST:$PORT  | Config: $CFG"
echo "   Using OPENAI_API_KEY:    ${OPENAI_API_KEY:0:7}…${OPENAI_API_KEY: -4}"
echo "   Using ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:7}…${ANTHROPIC_API_KEY: -4}"
echo "   (No master_key required; ensure hybrid.yaml has master_key: \"\")"
exec litellm --host "$HOST" --port "$PORT" --config "$CFG"
