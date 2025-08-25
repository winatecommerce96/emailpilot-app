# create the script
mkdir -p /emailpilot-app/scripts
cat > /emailpilot-app/scripts/install_awesome_claude_agents.sh <<'BASH'
#!/usr/bin/env bash
# Safe, non-destructive installer for Awesome Claude Agents + gpt-5 wiring
set -euo pipefail

# --- Config (override via env) ---
PROJECT_ROOT="${PROJECT_ROOT:-/emailpilot-app}"
REPO_URL="${REPO_URL:-https://github.com/vijaythecoder/awesome-claude-agents.git}"
VENDOR_DIR="${PROJECT_ROOT}/.vendor"
CLONE_DIR="${VENDOR_DIR}/awesome-claude-agents"
USER_AGENTS_DIR="${HOME}/.claude/agents"
PROJECT_CLAUDE_DIR="${PROJECT_ROOT}/.claude"
SETTINGS_JSON="${PROJECT_CLAUDE_DIR}/settings.json"
SETTINGS_LOCAL_JSON="${PROJECT_CLAUDE_DIR}/settings.local.json"
LAUNCHER="${PROJECT_ROOT}/scripts/claude_gpt5.sh"
GITIGNORE="${PROJECT_ROOT}/.gitignore"

# --- Preflight checks ---
command -v git >/dev/null || { echo "❌ git not found"; exit 1; }
command -v claude >/dev/null || { echo "❌ Claude CLI not found. Install it first, then rerun."; exit 1; }
[ -d "$PROJECT_ROOT" ] || { echo "❌ PROJECT_ROOT not found: $PROJECT_ROOT"; exit 1; }

echo "📁 Project root: $PROJECT_ROOT"
mkdir -p "$VENDOR_DIR" "$USER_AGENTS_DIR" "$PROJECT_CLAUDE_DIR" "${PROJECT_ROOT}/scripts"

# --- Clone or update the agents repo into a hidden vendor dir (non-destructive) ---
if [ -d "$CLONE_DIR/.git" ]; then
  echo "🔄 Updating existing agents repo at $CLONE_DIR"
  git -C "$CLONE_DIR" fetch --quiet
  git -C "$CLONE_DIR" pull --ff-only --quiet
else
  echo "⬇️  Cloning agents into $CLONE_DIR"
  git clone --depth=1 "$REPO_URL" "$CLONE_DIR" >/dev/null
fi

# --- Symlink into ~/.claude/agents (preserves any existing agents) ---
SRC_AGENTS="${CLONE_DIR}/agents"
DEST_LINK="${USER_AGENTS_DIR}/awesome-claude-agents"
if [ -e "$DEST_LINK" ] && [ ! -L "$DEST_LINK" ]; then
  ts=$(date +%Y%m%d-%H%M%S)
  echo "🛟 Backing up existing $DEST_LINK -> ${DEST_LINK}.backup.${ts}"
  mv "$DEST_LINK" "${DEST_LINK}.backup.${ts}"
fi
ln -sfn "$SRC_AGENTS" "$DEST_LINK"
echo "🔗 Linked $DEST_LINK -> $SRC_AGENTS"

# --- Project-scoped Claude settings (non-destructive) ---
# Shared (safe-to-commit) settings
if [ ! -f "$SETTINGS_JSON" ]; then
  cat > "$SETTINGS_JSON" <<'JSON'
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:4000",
    "ANTHROPIC_MODEL": "gpt-5",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "4096"
  },
  "permissions": {
    "deny": ["Read(./.env)", "Read(./secrets/**)"]
  }
}
JSON
  echo "🧠 Wrote $SETTINGS_JSON"
else
  echo "ℹ️  $SETTINGS_JSON exists; leaving it untouched."
fi

# Local (git-ignored) settings — do NOT populate secrets here
if [ ! -f "$SETTINGS_LOCAL_JSON" ]; then
  cat > "$SETTINGS_LOCAL_JSON" <<'JSON'
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "REPLACE_WITH_LITELLM_MASTER_KEY"
  }
}
JSON
  echo "🔒 Wrote $SETTINGS_LOCAL_JSON (placeholder token)"
else
  echo "ℹ️  $SETTINGS_LOCAL_JSON exists; leaving it untouched."
fi

# --- Launcher: start Claude wired to your gpt-5 gateway (no secrets stored) ---
cat > "$LAUNCHER" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ROOT="${PROJECT_ROOT:-/emailpilot-app}"
ENV_FILE="${ROOT}/.env"
if [ -f "$ENV_FILE" ]; then set -a; source "$ENV_FILE"; set +a; fi
: "${LITELLM_MASTER_KEY:?LITELLM_MASTER_KEY missing in .env or env}"

export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-http://127.0.0.1:4000}"
export ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-$LITELLM_MASTER_KEY}"
export ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-gpt-5}"
export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-4096}"

echo "🤖 Claude → $ANTHROPIC_BASE_URL | model=$ANTHROPIC_MODEL | max_tokens=$CLAUDE_CODE_MAX_OUTPUT_TOKENS"
exec claude "$@"
SH
chmod +x "$LAUNCHER"
echo "🚀 Launcher ready: $LAUNCHER"

# --- Ensure we don't commit secrets ---
touch "$GITIGNORE"
add_ignore() {
  local p="$1"
  grep -qxF "$p" "$GITIGNORE" || echo "$p" >> "$GITIGNORE"
}
add_ignore ".env"
add_ignore ".claude/settings.local.json"
echo "🛡️  Updated $GITIGNORE to ignore secrets."

echo
echo "✅ Done."
echo "Next steps:"
echo "1) Make sure your LiteLLM proxy is running on 127.0.0.1:4000 and advertises model 'gpt-5'."
echo "2) Put your LITELLM_MASTER_KEY in ${PROJECT_ROOT}/.env (or export it in your shell)."
echo "3) Start Claude with: ${LAUNCHER}"
echo "   Then run: /status   (should show Base URL 127.0.0.1:4000 and model gpt-5)"
echo "   And:      /agents   (should list awesome-claude-agents/*)"
BASH

# make it executable and run
chmod +x /emailpilot-app/scripts/install_awesome_claude_agents.sh
bash /emailpilot-app/scripts/install_awesome_claude_agents.sh
