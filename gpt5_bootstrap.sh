#!/usr/bin/env bash
# gpt5_bootstrap.sh — One-command setup: backup + files + local LiteLLM gateway
# Usage: ./gpt5_bootstrap.sh
set -euo pipefail
PROJECT_DIR="${PROJECT_DIR:-$PWD}"
TS="$(date +%Y%m%d-%H%M%S)"

say() { printf "\033[1;36m%s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m%s\033[0m\n" "$*"; }
err() { printf "\033[1;31m%s\033[0m\n" "$*"; }

# 0) Git snapshot (optional but recommended)
if command -v git >/dev/null 2>&1 && [ -d .git ]; then
  say "Creating Git snapshot…"
  git add -A || true
  git commit -m "pre-gpt5 baseline" || true
  git tag -f pre-gpt5-setup || true
  git checkout -B gpt5-integration || true
else
  warn "Git repo not found; skipping snapshot."
fi

# 1) Backup Claude settings and env
say "Backing up Claude configuration…"
BACKUP_DIR="claude-backup-$TS"
mkdir -p "$BACKUP_DIR"
if [ -d ".claude" ]; then rsync -a ".claude/" "$BACKUP_DIR/project.claude/"; fi
if [ -d "$HOME/.claude" ]; then rsync -a "$HOME/.claude/" "$BACKUP_DIR/home.claude/"; fi
for f in CLAUDE.md; do [ -f "$f" ] && cp "$f" "$BACKUP_DIR/"; done
(printenv | grep -E '^(ANTHROPIC|OPENAI|HTTP_PROXY|HTTPS_PROXY|NO_PROXY)=' || true) > "$BACKUP_DIR/env.snapshot"
tar -czf "$BACKUP_DIR.tgz" "$BACKUP_DIR"
say "Backup archive: $BACKUP_DIR.tgz"

# 2) Install files (non-destructive)
say "Laying down GPT-5 config and helpers (non-destructive)…"
mkdir -p .claude/agents config/gpt5 scripts

# Write settings.gpt5.json if missing
if [ ! -f ".claude/settings.gpt5.json" ]; then
  cat > .claude/settings.gpt5.json <<'JSON'
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:4000",
    "ANTHROPIC_AUTH_TOKEN": ANTHROPIC_AUTH_TOKEN,
    "ANTHROPIC_MODEL": "sonnet",
    "ANTHROPIC_SMALL_FAST_MODEL": "haiku",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "81920"
  },
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(pip *)",
      "Bash(make *)",
      "Read(**/*)",
      "Write(**/*)",
      "Edit(**/*)",
      "MultiEdit(**/*)",
      "Grep(**/*)",
      "Glob(**/*)"
    ],
    "deny": [
      "Read(./.env*)",
      "Read(./secrets/**)",
      "Bash(curl *)"
    ],
    "defaultMode": "askMe"
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 - <<'PY'\\nimport json,sys\\nreq=json.load(sys.stdin)\\nfp=req.get('tool_input',{}).get('file_path','')\\nfor bad in ('.env','/secrets/','id_rsa','config/credentials'):\\n    if bad in fp:\\n        sys.exit(2)\\nPY"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "if [ -f package.json ]; then npm test --silent || true; fi; if [ -f pyproject.toml ] || [ -f requirements.txt ]; then pytest -q || true; fi"
          }
        ]
      }
    ]
  }
}
JSON
else
  warn ".claude/settings.gpt5.json exists; leaving it."
fi

# Agent files
for F in planner.md qa-reviewer.md test-runner.md; do
  if [ ! -f ".claude/agents/$F" ]; then
    case "$F" in
      planner.md) cat > .claude/agents/planner.md <<'EOF'
---
name: planner
description: Strategic planner for multi-step tasks. Break work into verifiable steps with tests.
---
You are the PLANNER. Produce a minimal plan with checkpoints and commands. Avoid destructive actions.

EOF
        ;;
      qa-reviewer.md) cat > .claude/agents/qa-reviewer.md <<'EOF'
---
name: qa-reviewer
description: Code QA + security reviewer; block merges without tests passing.
tools: Read, Grep, Glob, Bash
---
You are the QA REVIEWER. Run tests/linters, summarize failures, and emit PASS/FAIL with a checklist.

EOF
        ;;
      test-runner.md) cat > .claude/agents/test-runner.md <<'EOF'
---
name: test-runner
description: Test executor; triage failures and propose surgical fixes.
tools: Bash, Read, Grep, Glob
---
You are the TEST RUNNER. Run the right subset of tests; when failures occur, localize and propose fixes.

EOF
        ;;
    esac
  else
    warn ".claude/agents/$F exists; leaving it."
  fi
done

# LiteLLM config
if [ ! -f "config/gpt5/litellm.yaml" ]; then
  cat > config/gpt5/litellm.yaml <<'YAML'
# config/gpt5/litellm.yaml
# LiteLLM proxy config to power Claude Code with OpenAI GPT‑5 via Anthropic-compatible endpoint
general_settings:
  master_key: sk-change-me
litellm_settings:
  drop_params: true
  set_verbose: true
model_list:
  - model_name: sonnet
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY
  - model_name: haiku
    litellm_params:
      model: openai/gpt-5-mini
      api_key: os.environ/OPENAI_API_KEY

YAML
fi

# CLAUDE_gpt5.md (do not overwrite CLAUDE.md)
if [ ! -f "CLAUDE_gpt5.md" ]; then
  cat > CLAUDE_gpt5.md <<'MD'
<!-- GPT‑5 Orchestration Policy: place at top of CLAUDE.md if adopting permanently -->
# Agent Policy (GPT‑5)
- Primary model: **GPT‑5 (alias: sonnet)**; background tasks: **GPT‑5‑mini (alias: haiku)**.
- Always Plan → Act → Verify with explicit tests.
- Prefer diffs/patches; summarize changes before writing.
- After significant edits, invoke **qa-reviewer** and **test-runner** subagents.
- Never read or edit `.env*`, `secrets/**`, SSH keys, or production credentials.
- On failures: localize, propose the minimal fix, re‑run tests.

MD
fi

# 3) Install/prepare LiteLLM proxy runner
cat > scripts/start_gpt5_gateway.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "ERROR: OPENAI_API_KEY not set"; exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found"; exit 1
fi
VENV=".gpt5-gateway"
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
. "$VENV/bin/activate"
pip install --upgrade pip
pip install "litellm[proxy]"
export LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-change-me}"
exec python -m litellm.proxy --port 4000 --host 0.0.0.0 --config config/gpt5/litellm.yaml
BASH
chmod +x scripts/start_gpt5_gateway.sh

# 4) Create a toggle runner (ephemeral env for the session)
cat > scripts/gpt5_toggle.sh <<'BASH'
#!/usr/bin/env bash
# Usage: scripts/gpt5_toggle.sh [gpt5|stock]
set -euo pipefail
MODE="${1:-}"
if [ -z "$MODE" ]; then echo "Usage: $0 [gpt5|stock]"; exit 1; fi
if [ "$MODE" = "gpt5" ]; then
  echo "🚀 Claude → GPT-5 (via http://localhost:4000)"
  ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-http://localhost:4000}"       ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-sk-change-me}"       ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-sonnet}"       ANTHROPIC_SMALL_FAST_MODEL="${ANTHROPIC_SMALL_FAST_MODEL:-haiku}"       claude
  exit $?
fi
if [ "$MODE" = "stock" ]; then
  echo "🔁 Claude → default provider (no overrides)"
  env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_MODEL -u ANTHROPIC_SMALL_FAST_MODEL claude
  exit $?
fi
echo "Unknown mode: $MODE"; exit 2
BASH
chmod +x scripts/gpt5_toggle.sh

# 5) Optional: apply the CLAUDE policy to CLAUDE.md (safe prepend with backup)
cat > scripts/gpt5_apply.sh <<'BASH'
#!/usr/bin/env bash
# Safe apply: prepend GPT‑5 policy to CLAUDE.md (creates backup); or --revert to restore
set -euo pipefail
if [ "${1:-}" = "--revert" ]; then
  latest=$(ls -1t CLAUDE.md.pre-gpt5.* 2>/dev/null | head -n1 || true)
  if [ -n "$latest" ]; then
    mv "$latest" CLAUDE.md
    echo "Restored CLAUDE.md from $latest"
  else
    echo "No backup found"; exit 1
  fi
  exit 0
fi
if [ ! -f CLAUDE.md ]; then
  echo "No CLAUDE.md to modify; aborting."; exit 1
fi
stamp="$(date +%Y%m%d-%H%M%S)"
cp CLAUDE.md "CLAUDE.md.pre-gpt5.$stamp"
{ head -n 1 CLAUDE.md | grep -q 'GPT‑5 Orchestration Policy' ; } && { echo "Already applied."; exit 0; } || true
cat CLAUDE_gpt5.md CLAUDE.md > CLAUDE.tmp && mv CLAUDE.tmp CLAUDE.md
echo "Applied GPT‑5 policy to CLAUDE.md (backup at CLAUDE.md.pre-gpt5.$stamp)"
BASH
chmod +x scripts/gpt5_apply.sh

say "Done. Next steps:"
cat <<'NEXT'
1) Start the local GPT-5 gateway (new terminal):
   OPENAI_API_KEY=sk-... LITELLM_MASTER_KEY=sk-change-me ./scripts/start_gpt5_gateway.sh

2) Launch Claude in GPT-5 mode (this terminal):
   ./scripts/gpt5_toggle.sh gpt5

3) Go back to your original provider:
   ./scripts/gpt5_toggle.sh stock

4) (Optional) Permanently add the GPT‑5 policy to CLAUDE.md:
   ./scripts/gpt5_apply.sh
   # Revert:
   ./scripts/gpt5_apply.sh --revert
NEXT
