#!/usr/bin/env bash
set -euo pipefail

PORT="8000"
APP="main_firestore:app"
ENV_FILE=".env"

kill_port() {
  local p="$1"
  if lsof -ti tcp:"$p" >/dev/null 2>&1; then
    echo "⚠️  Port $p is in use. Killing process(es)..."
    lsof -ti tcp:"$p" | xargs -r kill -9
    sleep 0.5
  fi
}

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

kill_port "$PORT"

echo "🗄️  Starting FastAPI backend on http://127.0.0.1:$PORT ..."
exec uvicorn "$APP" --host 127.0.0.1 --port "$PORT" --reload
