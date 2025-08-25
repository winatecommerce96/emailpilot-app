#!/usr/bin/env bash
# Lightweight launcher for the EmailPilot Claude agent (no gpt5, native Claude only)
# Usage:
#   scripts/emailpilot_agent.sh "use @emailpilot-engineer to <task>"

set -euo pipefail

if command -v claude >/dev/null 2>&1; then
  exec claude "$@"
fi

if command -v npx >/dev/null 2>&1; then
  CLI_VERSION="${CLAUDE_CLI_VERSION:-latest}"
  exec npx -y "npm:@anthropic-ai/claude-code@${CLI_VERSION}" "$@"
fi

echo "Error: Claude Code CLI is not installed and npx was not found in PATH." >&2
echo "Install the CLI or run: npm install -g @anthropic-ai/claude-code" >&2
exit 1

