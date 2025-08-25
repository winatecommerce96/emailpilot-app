#!/usr/bin/env bash
# scripts/claude_cloud.sh
# Launch Claude Code with no local gateway; pure cloud defaults.
set -euo pipefail

# Nuke any overrides that pointed at local proxies/gateways
unset ANTHROPIC_BASE_URL ANTHROPIC_API_BASE ANTHROPIC_AUTH_TOKEN ANTHROPIC_MODEL CLAUDE_CODE_MAX_OUTPUT_TOKENS

# If you want to force a specific CLI version, set CLAUDE_CLI_VERSION=1.0.61 before running.
# Otherwise we'll use 'latest' to get current cloud behavior.
VER="${CLAUDE_CLI_VERSION:-latest}"

echo "💬 Launching Claude Code (cloud) — CLI version: $VER"
echo "   No local gateway, no base URL overrides."
echo "   Tip: If prompted, /login in the REPL. Or pre-set ANTHROPIC_API_KEY before running this script."

exec npx -y "npm:@anthropic-ai/claude-code@${VER}" "$@"
