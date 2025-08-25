#!/usr/bin/env bash
set -euo pipefail
ROOT="${PROJECT_ROOT:-$(pwd)}"
VENV="$ROOT/.mini-proxy"
APP="$ROOT/anthropic_mapper.py"
HOST="${MAPPER_HOST:-127.0.0.1}"
PORT="${MAPPER_PORT:-4050}"

# Load .env for ANTHROPIC_API_KEY
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a; source "$ENV_FILE"; set +a
fi
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY in .env or env}"

python3 -m venv "$VENV" 2>/dev/null || true
source "$VENV/bin/activate"
pip -q install -U pip fastapi uvicorn[standard] httpx

# Kill anything already on the port
lsof -ti tcp:$PORT 2>/dev/null | xargs -r kill -9 || true

echo "🚀 Mapper → http://$HOST:$PORT  (alias: gpt-5 → Sonnet)"
exec uvicorn anthropic_mapper:app --host "$HOST" --port "$PORT"
