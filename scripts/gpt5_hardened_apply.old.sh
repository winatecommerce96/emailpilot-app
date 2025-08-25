#!/bin/bash
set -e
echo "🚀 Applying GPT-5 Hardened QA Pack..."

# Create git branch/tag backup
if git rev-parse --git-dir > /dev/null 2>&1; then
    git checkout -b gpt5-hardened-setup-$(date +%s)
    git tag pre-gpt5-hardened-$(date +%s)
fi

# Backup existing dirs/files
for target in .claude Makefile tests/smoke config/gpt5; do
    if [ -e "$target" ]; then
        echo "Backing up $target"
        mv "$target" "$target.bak.$(date +%s)"
    fi
done

# Create structure
mkdir -p .claude/agents tests/smoke config/gpt5 scripts

# Settings
cat > .claude/settings.gpt5.json <<'EOT'
{
  "model": "gpt-5",
  "qa_strict": true,
  "lint": {
    "python": ["ruff", "mypy --strict"],
    "javascript": ["tsc --noEmit", "eslint --max-warnings=0"]
  },
  "smoke_test_command": "make smoke"
}
EOT

# Agents
echo "# Planner Agent" > .claude/agents/planner.md
echo "# QA Reviewer Agent" > .claude/agents/qa-reviewer.md
echo "# Test Runner Agent" > .claude/agents/test-runner.md

# LiteLLM config
mkdir -p config/gpt5
cat > config/gpt5/litellm.yaml <<'EOT'
model_aliases:
  backend_developer: gpt-5
  qa_reviewer: gpt-5
EOT

# Makefile
cat > Makefile <<'EOT'
APP_MODULE?=main:app
APP_PORT?=8000

smoke:
	uvicorn $(APP_MODULE) --port $(APP_PORT) --lifespan off &
	PID=$$!; sleep 2; curl -f http://127.0.0.1:$(APP_PORT)/health; kill $$PID

up:
	uvicorn $(APP_MODULE) --reload --port $(APP_PORT)

down:
	pkill -f "uvicorn $(APP_MODULE)"
EOT

# Smoke tests
mkdir -p tests/smoke
cat > tests/smoke/test_health.py <<'EOT'
import requests

def test_health():
    r = requests.get("http://127.0.0.1:8000/health")
    assert r.status_code == 200
EOT

cat > tests/smoke/test_contract.py <<'EOT'
def test_contract():
    # placeholder for contract tests
    assert True
EOT

# Helper scripts
cat > scripts/start_gpt5_gateway.sh <<'EOT'
#!/bin/bash
litellm --config config/gpt5/litellm.yaml
EOT
chmod +x scripts/start_gpt5_gateway.sh

cat > scripts/gpt5_toggle.sh <<'EOT'
#!/bin/bash
if [ "$1" == "gpt5" ]; then
    cp .claude/settings.gpt5.json .claude/settings.json
    echo "Now using GPT-5"
elif [ "$1" == "stock" ]; then
    git checkout .claude/settings.json
    echo "Reverted to stock"
else
    echo "Usage: $0 [gpt5|stock]"
fi
EOT
chmod +x scripts/gpt5_toggle.sh

cat > scripts/install_smoke_deps.sh <<'EOT'
#!/bin/bash
pip install requests uvicorn ruff mypy eslint typescript
EOT
chmod +x scripts/install_smoke_deps.sh

echo "✅ GPT-5 Hardened QA Pack applied."
