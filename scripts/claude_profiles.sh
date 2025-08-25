#!/usr/bin/env bash
# scripts/claude_profiles.sh — Launch Claude Code with cost-tiered model profiles via your LiteLLM gateway
# Usage:
#   ./scripts/claude_profiles.sh heavy        # GPT-5 (primary) + haiku (fast = gpt-5-mini)
#   ./scripts/claude_profiles.sh standard     # Claude Sonnet native + haiku (fast)
#   ./scripts/claude_profiles.sh budget       # gpt-5-mini everywhere
#   ./scripts/claude_profiles.sh opus         # Claude Opus native + haiku (fast)
#   ./scripts/claude_profiles.sh native-haiku # Claude Haiku native
#
# Notes:
# - Requires your gateway on http://127.0.0.1:4000 (scripts/start_gpt5_soft.sh)
# - If you kept auth on, LITELLM_MASTER_KEY must be set (Bearer token). Otherwise, unset it.
# - Expects OPENAI_API_KEY (for GPT-5) and ANTHROPIC_API_KEY (for native Sonnet/Opus/Haiku) in .env or env.

set -euo pipefail

PROFILE="${1:-heavy}"
shift || true

ROOT="${PROJECT_ROOT:-$(pwd)}"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }

BASE="http://127.0.0.1:4000"
CLI_VERSION="${CLAUDE_CLI_VERSION:-1.0.61}"

# Point Claude at the gateway
export ANTHROPIC_BASE_URL="$BASE"
export ANTHROPIC_API_BASE="$BASE"

# Auth header for gateway, if enabled
if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then
  export ANTHROPIC_AUTH_TOKEN="Bearer ${LITELLM_MASTER_KEY}"
else
  unset ANTHROPIC_AUTH_TOKEN
fi

# Reasonable default cap to avoid CLI crashes on oversized values
export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-4096}"

case "$PROFILE" in
  heavy)
    export ANTHROPIC_MODEL="gpt-5"                 # -> openai/gpt-5
    export ANTHROPIC_SMALL_FAST_MODEL="haiku"      # -> openai/gpt-5-mini (mapped in YAML)
    ;;
  standard)
    export ANTHROPIC_MODEL="claude-3-5-sonnet-20240620"    # native Sonnet (requires ANTHROPIC_API_KEY in gateway env)
    export ANTHROPIC_SMALL_FAST_MODEL="claude-3-5-haiku-20241022"
    ;;
  budget)
    export ANTHROPIC_MODEL="haiku"                 # -> openai/gpt-5-mini
    export ANTHROPIC_SMALL_FAST_MODEL="haiku"
    ;;
  opus)
    export ANTHROPIC_MODEL="claude-3-opus-20240229"        # native Opus (requires ANTHROPIC_API_KEY)
    export ANTHROPIC_SMALL_FAST_MODEL="claude-3-5-haiku-20241022"
    ;;
  native-haiku)
    export ANTHROPIC_MODEL="claude-3-5-haiku-20241022"     # native Haiku
    export ANTHROPIC_SMALL_FAST_MODEL="claude-3-5-haiku-20241022"
    ;;
  *)
    echo "Unknown profile: $PROFILE"
    echo "Valid: heavy | standard | budget | opus | native-haiku"
    exit 2
    ;;
esac

echo "📎 Profile: $PROFILE"
echo "  Base URL: $ANTHROPIC_BASE_URL"
echo "  Model:    $ANTHROPIC_MODEL"
echo "  Fast:     $ANTHROPIC_SMALL_FAST_MODEL"
if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then echo "  Auth:     Bearer (gateway)"; else echo "  Auth:     none"; fi

exec npx -y "npm:@anthropic-ai/claude-code@${CLI_VERSION}" "$@"
