#!/usr/bin/env bash
# scripts/claude_gateway_hybrid_mk.sh
# Claude Code → local LiteLLM (hybrid) with Master-Key auth
set -euo pipefail
ROOT="${PROJECT_ROOT:-$(pwd)}"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }

export ANTHROPIC_BASE_URL="http://127.0.0.1:4000"
# Send ONLY the proxy master key to the gateway
: "${LITELLM_MASTER_KEY:?Set LITELLM_MASTER_KEY in .env or env}"
export ANTHROPIC_AUTH_TOKEN="Bearer ${LITELLM_MASTER_KEY}"

# Ensure we don't accidentally send provider keys from this shell
unset ANTHROPIC_API_KEY OPENAI_API_KEY ANTHROPIC_API_BASE

# Let agents choose model via front-matter; or set a default fallback:
# export ANTHROPIC_MODEL="gpt-5"
export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-4096}"

echo "💬 Claude Code → $ANTHROPIC_BASE_URL (master-key auth)"
echo "   Using token: Bearer ${LITELLM_MASTER_KEY:0:6}…${LITELLM_MASTER_KEY: -4}"
exec npx -y "npm:@anthropic-ai/claude-code@${CLAUDE_CLI_VERSION:-1.0.61}" "$@"
