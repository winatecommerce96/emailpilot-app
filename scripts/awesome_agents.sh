set -euo pipefail

# --- Figure out PROJECT_ROOT safely ---
if [[ -n "${PROJECT_ROOT:-}" && -d "$PROJECT_ROOT" ]]; then
  ROOT="$PROJECT_ROOT"
elif git rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT="$(git rev-parse --show-toplevel)"
else
  ROOT="$PWD"
fi
if [[ ! -d "$ROOT" ]]; then
  echo "❌ PROJECT_ROOT not found: $ROOT"; exit 1
fi

REPO_URL="${REPO_URL:-https://github.com/vijaythecoder/awesome-claude-agents.git}"
VENDOR_DIR="$ROOT/.vendor"
CLONE_DIR="$VENDOR_DIR/awesome-claude-agents"
USER_AGENTS_DIR="$HOME/.claude/agents"
PROJECT_CLAUDE_DIR="$ROOT/.claude"
SETTINGS_JSON="$PROJECT_CLAUDE_DIR/settings.json"
SETTINGS_LOCAL_JSON="$PROJECT_CLAUDE_DIR/settings.local.json"
LAUNCHER="$ROOT/scripts/claude_gpt5.sh"
GITIGNORE="$ROOT/.gitignore"

echo "📁 Project root: $ROOT"

command -v git >/dev/null || { echo "❌ git not found"; exit 1; }
command -v claude >/dev/null || { echo "❌ Claude CLI not found. Install it and rerun."; exit 1; }

mkdir -p "$VENDOR_DIR" "$USER_AGENTS_DIR" "$PROJECT_CLAUDE_DIR" "$ROOT/scripts"

# Clone or update repo into hidden vendor dir
if [[ -d "$CLONE_DIR/.git" ]]; then
  echo "🔄 Updating $CLONE_DIR"
  git -C "$CLONE_DIR" fetch --quiet
  git -C "$CLONE_DIR" pull --ff-only --quiet
else
  echo "⬇️  Cloning into $CLONE_DIR"
  git clone --depth=1 "$REPO_URL" "$CLONE_DIR" >/dev/null
fi

# Symlink into ~/.claude/agents (non-destructive)
SRC_AGENTS="$CLONE_DIR/agents"
DEST_LINK="$USER_AGENTS_DIR/awesome-claude-agents"
if [[ -e "$DEST_LINK" && ! -L "$DEST_LINK" ]]; then
  ts=$(date +%Y%m%d-%H%M%S)
  echo "🛟 Backing up $DEST_LINK -> ${DEST_LINK}.backup.${ts}"
  mv "$DEST_LINK" "${DEST_LINK}.backup.${ts}"
fi
ln -sfn "$SRC_AGENTS" "$DEST_LINK"
echo "🔗 Linked $DEST_LINK -> $SRC_AGENTS"

# Project-scoped Claude settings (safe to commit)
if [[ ! -f "$SETTINGS_JSON" ]]; then
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
  echo "ℹ️  $SETTINGS_JSON exists; leaving it."
fi

# Local (git-ignored) settings with placeholder token
if [[ ! -f "$SETTINGS_LOCAL_JSON" ]]; then
  cat > "$SETTINGS_LOCAL_JSON" <<'JSON'
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "REPLACE_WITH_LITELLM_MASTER_KEY"
  }
}
JSON
  echo "🔒 Wrote $SETTINGS_LOCAL_JSON (placeholder)"
else
  echo "ℹ️  $SETTINGS_LOCAL_JSON exists; leaving it."
fi

# Launcher pointing Claude at your LiteLLM gateway
cat > "$LAUNCHER" <<'SH'
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
SH
chmod +x "$LAUNCHER"
echo "🚀 Launcher ready: $LAUNCHER"

# Don’t commit secrets
touch "$GITIGNORE"
grep -qxF ".env" "$GITIGNORE" || echo ".env" >> "$GITIGNORE"
grep -qxF ".claude/settings.local.json" "$GITIGNORE" || echo ".claude/settings.local.json" >> "$GITIGNORE"
echo "🛡️  Updated $GITIGNORE to ignore secrets."

echo
echo "✅ Done."
echo "Next:"
echo "1) Ensure your LiteLLM proxy is running on 127.0.0.1:4000 (model alias 'gpt-5')."
echo "2) Put LITELLM_MASTER_KEY in $ROOT/.env."
echo "3) Start Claude with: $LAUNCHER"
echo "   In Claude: /status (Base URL 127.0.0.1:4000, Model gpt-5) and /agents."