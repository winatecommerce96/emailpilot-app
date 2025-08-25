set -euo pipefail

# 1) Ensure we are NOT pointing at any local gateways
unset ANTHROPIC_BASE_URL ANTHROPIC_API_BASE ANTHROPIC_AUTH_TOKEN ANTHROPIC_MODEL CLAUDE_CODE_MAX_OUTPUT_TOKENS

# 2) Optionally source project .env for ANTHROPIC_API_KEY (but do NOT require it here)
ROOT="${PROJECT_ROOT:-$(pwd)}"
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# 3) Prefer API key auth; avoid token/key conflict warnings
#    If a real ANTHROPIC_API_KEY is present, drop any lingering token
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  unset ANTHROPIC_AUTH_TOKEN
fi

# 4) Sanity checks
command -v claude >/dev/null 2>&1 || { echo "❌ 'claude' CLI not found. Install it and retry."; exit 1; }

# 5) Launch vanilla Claude (cloud)
exec claude "$@"