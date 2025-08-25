#!/usr/bin/env bash
# start_gpt5_gateway.sh — Anthropic via LiteLLM, locked to 127.0.0.1:4000

set -euo pipefail

GATEWAY_HOST="127.0.0.1"
GATEWAY_PORT="4000"
CFG="config/gpt5/litellm.yaml"
VENV=".gpt5-gateway"

# Load env (master key + Anthropic key live here)
if [[ -f ".env" ]]; then
  set -a
  source .env
  set +a
fi

# Require the secrets we actually use
: "${LITELLM_MASTER_KEY:?ERROR: LITELLM_MASTER_KEY is not set}"
: "${ANTHROPIC_API_KEY:?ERROR: ANTHROPIC_API_KEY is not set}"

# Avoid accidental port/env overrides
unset PORT

# Isolate deps
[ -d "$VENV" ] || python3 -m venv "$VENV"
source "$VENV/bin/activate"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet "litellm[proxy]"

# Masked key preview (last 4 only)
mask() { local s="$1"; echo "***${s: -4}"; }
echo "🔐 Auth: Authorization: Bearer $(mask "$LITELLM_MASTER_KEY")"
echo "🚀 LiteLLM → http://$GATEWAY_HOST:$GATEWAY_PORT  (config: $CFG)"

exec litellm --config "$CFG" --host "$GATEWAY_HOST" --port "$GATEWAY_PORT"
