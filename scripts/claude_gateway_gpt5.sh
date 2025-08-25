#!/usr/bin/env bash
# Launch Claude Code via gateway, pinned to a version that loads agents.
# - Points to http://127.0.0.1:4000 (start with scripts/start_gpt5_soft.sh)
# - Uses LITELLM_MASTER_KEY as Bearer token
# - Defaults model to gpt-5 (you can /model sonnet or /model haiku too)

set -euo pipefail
CLI_VERSION="${CLAUDE_CLI_VERSION:-1.0.61}"

# Avoid auth conflicts: prefer gateway token; clear API key
unset ANTHROPIC_API_KEY
export ANTHROPIC_BASE_URL="http://127.0.0.1:4000"
# Some builds look for ANTHROPIC_API_BASE; set both for safety
export ANTHROPIC_API_BASE="$ANTHROPIC_BASE_URL"

# Load .env for the master key
ROOT="${PROJECT_ROOT:-$(pwd)}"
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then set -a; source "$ENV_FILE"; set +a; fi
: "${LITELLM_MASTER_KEY:?ERROR: LITELLM_MASTER_KEY missing (set it in $ENV_FILE).}"
export ANTHROPIC_AUTH_TOKEN="Bearer ${LITELLM_MASTER_KEY:?set in .env}"

# Default model shown in /status; you can change inside REPL via /model
export ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-gpt-5}"
# Cap tokens to avoid 8192 errors on backends with lower max
export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-8200}"
export ANTHROPIC_SMALL_FAST_MODEL="${ANTHROPIC_SMALL_FAST_MODEL:-haiku}"  # also mapped above


command -v node >/dev/null || { echo "❌ Node.js not found."; exit 1; }
exec npx -y "npm:@anthropic-ai/claude-code@${CLI_VERSION}" "$@"