set -euo pipefail

# Detect project root
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT="$(git rev-parse --show-toplevel)"
else
  ROOT="$PWD"
fi

SRC="$ROOT/.vendor/awesome-claude-agents/agents"
[ -d "$SRC" ] || { echo "❌ Source not found: $SRC"; exit 1; }

# Targets (user + project)
USER_BASE="$HOME/.claude/agents"
USER_PACK="$USER_BASE/awesome-claude-agents-copy"
USER_PACK_FLAT="$USER_BASE/awesome-claude-agents-flat-copy"

PROJ_BASE="$ROOT/.claude/agents"
PROJ_PACK="$PROJ_BASE/awesome-claude-agents-copy"
PROJ_PACK_FLAT="$PROJ_BASE/awesome-claude-agents-flat-copy"

mkdir -p "$USER_BASE" "$PROJ_BASE"
rm -rf "$USER_PACK" "$USER_PACK_FLAT" "$PROJ_PACK" "$PROJ_PACK_FLAT"
mkdir -p "$USER_PACK" "$USER_PACK_FLAT" "$PROJ_PACK" "$PROJ_PACK_FLAT"

# Copy real files (no symlinks)
rsync -a --delete "$SRC/" "$USER_PACK/"
rsync -a --delete "$SRC/" "$PROJ_PACK/"

# Create flat mirrors of all .md files (helps CLIs that don't recurse)
while IFS= read -r -d '' f; do
  rel="${f#"$SRC/"}"
  safe="${rel//\//__}"
  install -m 0644 "$f" "$USER_PACK_FLAT/$safe"
  install -m 0644 "$f" "$PROJ_PACK_FLAT/$safe"
done < <(find "$SRC" -type f -name '*.md' -print0)

# Normalize YAML front-matter: ensure valid `name:` and `description:`
python3 - <<'PY'
import os, re, sys, pathlib, yaml
from pathlib import Path

def slugify(stem):
    s = stem.lower().replace(' ', '-')
    s = re.sub(r'[^a-z0-9\-]', '-', s)  # drop @ and other symbols
    s = re.sub(r'-+', '-', s).strip('-')
    return s or 'agent'

def fix_file(p: Path):
    t = p.read_text(encoding='utf-8', errors='ignore')
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', t, flags=re.S)
    if not m:
        # add minimal front-matter if missing
        name = slugify(p.stem)
        fm = {'name': name, 'description': f'Specialized subagent {name}.'}
        p.write_text('---\n' + yaml.safe_dump(fm, sort_keys=False) + '---\n' + t, encoding='utf-8')
        return
    fm_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except Exception:
        fm = {}
    changed = False
    if 'name' not in fm or not fm['name']:
        fm['name'] = slugify(p.stem); changed = True
    else:
        s = slugify(str(fm['name']))
        if s != fm['name']:
            fm['name'] = s; changed = True
    if 'description' not in fm or not fm['description']:
        fm['description'] = f'Specialized subagent {fm["name"]}.'; changed = True
    if changed:
        new_fm = yaml.safe_dump(fm, sort_keys=False)
        p.write_text('---\n' + new_fm + '---\n' + body, encoding='utf-8')

def sweep(root):
    for p in Path(root).rglob('*.md'):
        fix_file(p)

roots = [
    os.path.expanduser("~/.claude/agents/awesome-claude-agents-copy"),
    os.path.expanduser("~/.claude/agents/awesome-claude-agents-flat-copy"),
    os.path.join(os.environ.get("PWD","."),
                 ".claude/agents/awesome-claude-agents-copy"),
    os.path.join(os.environ.get("PWD","."),
                 ".claude/agents/awesome-claude-agents-flat-copy"),
]
for r in roots:
    if os.path.isdir(r):
        sweep(r)
PY

# Add a minimal smoke-test agent (project-scoped)
mkdir -p "$PROJ_BASE"
cat > "$PROJ_BASE/zzz-smoke-test.md" <<'MD'
---
name: smoke-test
description: Minimal subagent for discovery testing. Use explicitly to confirm /agents.
tools: Read, Grep
---
You are a simple verification agent. When invoked, print "discovered".
MD

# Report
echo "📦 Copied:"
echo "  - $USER_PACK"
echo "  - $USER_PACK_FLAT"
echo "  - $PROJ_PACK"
echo "  - $PROJ_PACK_FLAT"
echo "🧪 Smoke test: $PROJ_BASE/zzz-smoke-test.md"