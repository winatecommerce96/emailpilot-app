set -euo pipefail

# Detect project root
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT="$(git rev-parse --show-toplevel)"
else
  ROOT="$PWD"
fi

AGENTS_SRC="$ROOT/.vendor/awesome-claude-agents/agents"
USER_AGENTS="$HOME/.claude/agents"
USER_LINK="$USER_AGENTS/awesome-claude-agents"
USER_FLAT="$USER_AGENTS/awesome-claude-agents-flat"
PROJ_AGENTS="$ROOT/.claude/agents"
PROJ_LINK="$PROJ_AGENTS/awesome-claude-agents"
PROJ_FLAT="$PROJ_AGENTS/awesome-claude-agents-flat"

# Sanity
[ -d "$AGENTS_SRC" ] || { echo "❌ Source agents folder missing: $AGENTS_SRC"; exit 1; }

# Ensure parents
mkdir -p "$USER_AGENTS" "$PROJ_AGENTS"

# Symlink the tree (non-destructive refresh)
ln -sfn "$AGENTS_SRC" "$USER_LINK"
ln -sfn "$AGENTS_SRC" "$PROJ_LINK"

# Build flat views for CLIs that don't recurse folders
rm -rf "$USER_FLAT" "$PROJ_FLAT"
mkdir -p "$USER_FLAT" "$PROJ_FLAT"

# macOS find: no -maxdepth; we just traverse and link all .md files
while IFS= read -r -d '' f; do
  rel="${f#"$AGENTS_SRC/"}"
  # turn subpaths like core/planner.md -> core__planner.md
  safe="${rel//\//__}"
  ln -s "$f" "$USER_FLAT/$safe"
  ln -s "$f" "$PROJ_FLAT/$safe"
done < <(find "$AGENTS_SRC" -type f -name '*.md' -print0)

# Report
echo "📁 Project root: $ROOT"
echo "🔗 User link:    $USER_LINK -> $AGENTS_SRC"
echo "📚 User flat:    $(find "$USER_FLAT" -type l | wc -l | tr -d ' ') files"
echo "🔗 Project link: $PROJ_LINK -> $AGENTS_SRC"
echo "📚 Project flat: $(find "$PROJ_FLAT" -type l | wc -l | tr -d ' ') files"

echo "✅ Agents linked. If Claude still shows zero agents, run '/reload' inside the CLI."