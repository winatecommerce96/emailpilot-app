set -euo pipefail

TS="$(date +%Y%m%d-%H%M%S)"
USER_DIR="$HOME/.claude/agents"
PROJ_DIR="$(pwd)/.claude/agents"

backup_dir() {
  local d="$1"
  [ -d "$d" ] || return 0
  local b="${d}.backup.${TS}"
  cp -R "$d" "$b"
  echo "🛟 Backup: $d -> $b"
}

repair_dir() {
  local d="$1"
  [ -d "$d" ] || return 0
  python3 - "$d" <<'PY'
import sys, re, pathlib, yaml
from pathlib import Path

SAFE_TOOLS = {"Read","Grep","Write","Edit","Bash","Glob"}

def slugify(s):
    import re
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9\-]+','-', s)
    s = re.sub(r'-+','-', s).strip('-')
    return s or "agent"

def normalize_tools(v):
    if v is None: return None
    if isinstance(v, str):
        parts = [p.strip() for p in v.split(",")]
    elif isinstance(v, list):
        parts = [str(p).strip() for p in v]
    else:
        return None
    # keep only safe tools
    parts = [p for p in parts if p in SAFE_TOOLS]
    return parts or None

def clean_front_matter(p: Path):
    t = p.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', t, flags=re.S)
    if not m:
        # add minimal front matter
        fm = {"name": slugify(p.stem), "description": f"Subagent {p.stem}."}
        p.write_text('---\n'+yaml.safe_dump(fm, sort_keys=False)+'---\n'+t, encoding="utf-8")
        return True

    fm_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except Exception:
        fm = {}

    changed = False

    # drop unsupported keys commonly causing errors
    for bad in ["location","loc","where","area","mcp_servers","mcpServers","permissions","context","persona","goals","role"]:
        if bad in fm:
            fm.pop(bad, None); changed = True

    # ensure name/description
    if not fm.get("name"):
        fm["name"] = slugify(p.stem); changed = True
    else:
        s = slugify(str(fm["name"]))
        if s != fm["name"]:
            fm["name"] = s; changed = True
    if not fm.get("description"):
        fm["description"] = f"Subagent {fm['name']}."; changed = True

    # normalize tools
    if "tools" in fm:
        tools = normalize_tools(fm.get("tools"))
        if tools:
            if tools != fm["tools"]:
                fm["tools"] = tools; changed = True
        else:
            fm.pop("tools", None); changed = True

    if changed:
        new_fm = yaml.safe_dump(fm, sort_keys=False)
        p.write_text('---\n'+new_fm+'---\n'+body, encoding="utf-8")
        print(f"✔ fixed: {p}")
    return changed

root = Path(sys.argv[1])
for md in root.rglob("*.md"):
    try:
        clean_front_matter(md)
    except Exception as e:
        print(f"⚠️  skipped (parse error): {md} -> {e}")
PY
}