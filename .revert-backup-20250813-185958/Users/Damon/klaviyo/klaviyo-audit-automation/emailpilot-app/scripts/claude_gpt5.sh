#!/usr/bin/env bash
set -euo pipefail
ROOT="${PROJECT_ROOT:-$(pwd)}"
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then set -a; source "$ENV_FILE"; set +a; fi
: "${LITELLM_MASTER_KEY:?LITELLM_MASTER_KEY missing in .env or env}"

export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-http://127.0.0.1:4000}"
export ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-$LITELLM_MASTER_KEY}"
export ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-gpt-5}"
export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-4096}"

echo "🤖 Claude → $ANTHROPIC_BASE_URL | model=$ANTHROPIC_MODEL | max_tokens=$CLAUDE_CODE_MAX_OUTPUT_TOKENS"
exec claude "$@"
