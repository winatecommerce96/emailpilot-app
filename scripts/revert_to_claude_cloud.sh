#!/usr/bin/env bash
# scripts/revert_to_claude_cloud.sh
# Roll back to a clean, cloud-only Claude Code install (no LiteLLM).
# Preserves conversation history (sessions) but resets settings/agents.
set -euo pipefail

ROOT="${PROJECT_ROOT:-$(pwd)}"
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$ROOT/claude-backup-$TS"
HOME_CLAUDE="$HOME/.claude"
PROJ_CLAUDE="$ROOT/.claude"

echo "📦 Backing up Claude data to: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# 0) Stop local gateways on :4000 if any
echo "🛑 Stopping any local gateways on :4000"
lsof -ti tcp:4000 2>/dev/null | xargs -r kill -9 || true
# Try to stop any uvicorn/litellm we started in project venvs
pgrep -f "litellm|uvicorn|.gpt5-" >/dev/null 2>&1 && pkill -f "litellm|uvicorn|.gpt5-" || true

# 1) Backup + reset HOME-level ~/.claude
if [[ -d "$HOME_CLAUDE" ]]; then
  echo "🗃  Backing up $HOME_CLAUDE → $BACKUP_DIR/home.claude"
  rsync -a "$HOME_CLAUDE/" "$BACKUP_DIR/home.claude/"

  echo "🧹 Resetting $HOME_CLAUDE to minimal clean state (sessions preserved)"
  # Save sessions aside
  tmp_sessions="$(mktemp -d)"
  if [[ -d "$HOME_CLAUDE/sessions" ]]; then
    rsync -a "$HOME_CLAUDE/sessions/" "$tmp_sessions/"
  fi
  rm -rf "$HOME_CLAUDE"
  mkdir -p "$HOME_CLAUDE/sessions"
  # Restore sessions only
  if [[ -d "$tmp_sessions" ]]; then
    rsync -a "$tmp_sessions/" "$HOME_CLAUDE/sessions/" || true
    rm -rf "$tmp_sessions"
  fi
fi

# 2) Backup + reset PROJECT-level ./.claude
if [[ -d "$PROJ_CLAUDE" ]]; then
  echo "🗃  Backing up $PROJ_CLAUDE → $BACKUP_DIR/project.claude"
  rsync -a "$PROJ_CLAUDE/" "$BACKUP_DIR/project.claude/"
  echo "🧹 Removing project .claude (fresh start; sessions live in HOME scope)"
  rm -rf "$PROJ_CLAUDE"
fi

# 3) Quarantine any project venvs created for gateways
for v in ".gpt5-soft" ".gpt5-hybrid" ".gpt5-gateway" ".mini-proxy"; do
  if [[ -d "$ROOT/$v" ]]; then
    echo "🧳 Moving $v → $BACKUP_DIR/$v"
    mv "$ROOT/$v" "$BACKUP_DIR/$v"
  fi
done

# 4) Quarantine gateway configs (non-destructive)
if [[ -d "$ROOT/config/gpt5" ]]; then
  echo "🧳 Moving config/gpt5 → $BACKUP_DIR/config.gpt5"
  mv "$ROOT/config/gpt5" "$BACKUP_DIR/config.gpt5"
fi

# 5) Print env guidance (cannot unset parent shell vars from here unless sourced)
cat <<'ENVMSG'

✅ Revert complete.
Next steps (run in a NEW terminal so prior env vars are gone), or copy/paste:

  # Ensure no gateway overrides are set in this shell:
  unset ANTHROPIC_BASE_URL ANTHROPIC_API_BASE ANTHROPIC_AUTH_TOKEN ANTHROPIC_MODEL CLAUDE_CODE_MAX_OUTPUT_TOKENS

  # Optional: if you prefer API key auth instead of login flow, export it here:
  # export ANTHROPIC_API_KEY=sk-ant-...

  # Launch Claude Code (pure cloud):
  scripts/claude_cloud.sh

Your full backup lives here:
  BACKUP: $BACKUP_DIR

Sessions preserved:
  - $HOME/.claude/sessions

If you ever need to restore other bits (agents/settings), copy selectively from:
  - $BACKUP_DIR/home.claude/
  - $BACKUP_DIR/project.claude/
ENVMSG
