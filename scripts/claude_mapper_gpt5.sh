#!/usr/bin/env bash
set -euo pipefail
unset ANTHROPIC_BASE_URL ANTHROPIC_API_BASE ANTHROPIC_AUTH_TOKEN ANTHROPIC_MODEL CLAUDE_CODE_MAX_OUTPUT_TOKENS
ROOT="${PROJECT_ROOT:-$(pwd)}"
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then set -a; source "$ENV_FILE"; set +a; fi
HOST="${MAPPER_HOST:-127.0.0.1}"
PORT="${MAPPER_PORT:-4050}"
export ANTHROPIC_BASE_URL="http://$HOST:$PORT"
export ANTHROPIC_MODEL="gpt-5"
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY in .env or env}"
exec npx -y "npm:@anthropic-ai/claude-code@${CLAUDE_CLI_VERSION:-1.0.61}" "$@"
