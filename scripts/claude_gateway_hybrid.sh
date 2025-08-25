#!/usr/bin/env bash
# scripts/claude_gateway_hybrid.sh — Claude Code pointed at local LiteLLM (hybrid)
# Terminal B: run this AFTER the gateway is listening
set -euo pipefail

ROOT="${PROJECT_ROOT:-$(pwd)}"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }

# Point Claude Code at the local LiteLLM gateway
export ANTHROPIC_BASE_URL="http://127.0.0.1:4000"
unset ANTHROPIC_AUTH_TOKEN
unset ANTHROPIC_API_BASE

# Let agents choose model via front-matter (model: gpt-5 | gpt-5-mini | sonnet | haiku | opus)
# If you want a default fallback, uncomment ONE:
# export ANTHROPIC_MODEL="gpt-5"
# export ANTHROPIC_MODEL="sonnet"

export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-4096}"

echo "💬 Claude Code → $ANTHROPIC_BASE_URL"
echo "   Agent-defined models will be used."
exec npx -y "npm:@anthropic-ai/claude-code@${CLAUDE_CLI_VERSION:-1.0.61}" "$@"
