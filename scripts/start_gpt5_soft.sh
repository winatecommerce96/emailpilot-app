#!/usr/bin/env bash
# start_gpt5_soft.sh — Start a LOCAL LiteLLM Anthropic-compatible gateway that maps Claude IDs → OpenAI GPT‑5
# - Binds to 127.0.0.1:4000
# - Uses OPENAI_API_KEY for OpenAI backend calls
# - Optional: LITELLM_MASTER_KEY to require Authorization: Bearer ... on requests
# - DOES NOT overwrite config/gpt5/soft.yaml if it exists (creates a sane default otherwise)

set -euo pipefail

ROOT="${PROJECT_ROOT:-$(pwd)}"
CFG_DIR="$ROOT/config/gpt5"
CFG_FILE="$CFG_DIR/soft.yaml"
VENV="$ROOT/.gpt5-soft"
HOST="127.0.0.1"
PORT="4000"

mkdir -p "$CFG_DIR"

# Load .env if present (OPENAI_API_KEY / LITELLM_MASTER_KEY)
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

: "${OPENAI_API_KEY:?ERROR: OPENAI_API_KEY not set. Put it in .env or export it in this shell.}"

# Only write a default config if missing (extended map of Anthropic IDs → GPT‑5 / GPT‑5‑mini)
if [[ ! -f "$CFG_FILE" ]]; then
  cat > "$CFG_FILE" <<'YAML'
general_settings:
  telemetry: false
  master_key: ${LITELLM_MASTER_KEY:-}

proxy_settings:
  host: 127.0.0.1
  port: 4000
  cors: ["*"]

litellm_settings:
  set_verbose: true
  drop_params: true
  timeout: 120

model_list:
  # Aliases you'll pick inside Claude
  - model_name: gpt-5
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY
      timeout: 120

  - model_name: haiku
    litellm_params:
      model: openai/gpt-5-mini
      api_key: os.environ/OPENAI_API_KEY

  # Map common Anthropic IDs so Claude defaults also work
  - model_name: sonnet
    litellm_params: { model: openai/gpt-5, api_key: os.environ/OPENAI_API_KEY }
  - model_name: claude-3-5-sonnet-20240620
    litellm_params: { model: openai/gpt-5, api_key: os.environ/OPENAI_API_KEY }
  - model_name: claude-3-5-sonnet-latest
    litellm_params: { model: openai/gpt-5, api_key: os.environ/OPENAI_API_KEY }
  - model_name: claude-sonnet-4-20250514
    litellm_params: { model: openai/gpt-5, api_key: os.environ/OPENAI_API_KEY }
  - model_name: claude-sonnet-4-latest
    litellm_params: { model: openai/gpt-5, api_key: os.environ/OPENAI_API_KEY }

  # Haiku family → GPT‑5‑mini
  - model_name: claude-3-5-haiku-20241022
    litellm_params: { model: openai/gpt-5-mini, api_key: os.environ/OPENAI_API_KEY }
  - model_name: claude-3-5-haiku-latest
    litellm_params: { model: openai/gpt-5-mini, api_key: os.environ/OPENAI_API_KEY }
YAML
fi

# Kill anything already on the port
lsof -ti tcp:$PORT 2>/dev/null | xargs -r kill -9 || true

# Create & activate venv, install LiteLLM proxy
python3 -m venv "$VENV" 2>/dev/null || true
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip -q install -U pip "litellm[proxy]"

# Masked key printout
mask() { awk '{ if(length($0)<=10){print "<set>"} else {print substr($0,1,4) "…" substr($0,length($0)-3,4)} }'; }
MASTER_MSG="<none>"
if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then MASTER_MSG="Bearer $(printf %s "$LITELLM_MASTER_KEY" | mask)"; fi

echo "🔐 Expect header: Authorization: ${MASTER_MSG}"
echo "📝 Config: $CFG_FILE"
echo "🚀 LiteLLM → http://$HOST:$PORT (OpenAI backend)"

exec litellm --host "$HOST" --port "$PORT" --config "$CFG_FILE"
