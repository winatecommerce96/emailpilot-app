#!/usr/bin/env bash
# scripts/gpt5_hardened_apply.sh
# Generates a hardened LiteLLM config using the `litellm_params` schema.
# Fixes prior heredoc/validation bug and ensures newline-safe CORS.

set -euo pipefail

# --- Defaults (override via env or flags) ---
OUT_FILE="${OUT_FILE:-config/gpt5/litellm.yaml}"   # --out path.yaml
HOST="${GPT5_GATEWAY_HOST:-127.0.0.1}"              # --host 0.0.0.0
PORT="${GPT5_GATEWAY_PORT:-4000}"                   # --port 5000
MODEL_DEFAULT="anthropic/claude-3-5-sonnet-20240620"
MODEL="${ANTHROPIC_MODEL:-$MODEL_DEFAULT}"          # --model provider/model
CORS_CSV_DEFAULT="http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
CORS_CSV="${GPT5_GATEWAY_CORS:-$CORS_CSV_DEFAULT}"  # --cors "http://localhost:3000,http://127.0.0.1:3000"

STRICT=0
usage() {
  cat <<USAGE
Usage:
  $(basename "$0") [--model <provider/model>] [--host <host>] [--port <port>] \\
                   [--cors "<csv>"] [--out <path.yaml>] [--strict]
USAGE
}

# --- Parse flags ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) MODEL="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --cors) CORS_CSV="$2"; shift 2 ;;
    --out) OUT_FILE="$2"; shift 2 ;;
    --strict) STRICT=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

OUT_DIR="$(dirname "$OUT_FILE")"
mkdir -p "$OUT_DIR"

# Load .env for local dev convenience
if [[ -f .env ]]; then
  # shellcheck disable=SC1090
  source .env || true
fi

# Strict mode: enforce keys exist now (otherwise referenced at runtime)
if [[ "$STRICT" -eq 1 ]]; then
  [[ -n "${LITELLM_MASTER_KEY:-}" ]] || { echo "❌ STRICT: LITELLM_MASTER_KEY not set"; exit 1; }
  [[ -n "${ANTHROPIC_API_KEY:-}" ]] || { echo "❌ STRICT: ANTHROPIC_API_KEY not set"; exit 1; }
fi

# Build properly indented YAML list for CORS (4 spaces)
IFS=',' read -r -a CORS_ITEMS <<< "$CORS_CSV"
CORS_YAML=""
for origin in "${CORS_ITEMS[@]}"; do
  o="$(echo "$origin" | xargs)"
  [[ -z "$o" ]] && continue
  CORS_YAML+="    - \"$o\"\n"
done
# Fallback if empty
if [[ -z "$CORS_YAML" ]]; then
  CORS_YAML="    - \"http://localhost:5173\"\n    - \"http://127.0.0.1:5173\"\n"
fi

# --- Write YAML (ensure newline after injected CORS block) ---
cat > "$OUT_FILE" <<YAML
general_settings:
  telemetry: false
  master_key: os.environ/LITELLM_MASTER_KEY

proxy_settings:
  host: ${HOST}
  port: ${PORT}
  cors:
$(printf "%b" "$CORS_YAML")
  jwt_auth: false
  enforce_user_provided_key: false

litellm_settings:
  drop_params: true
  set_verbose: false
  num_workers: 1

model_list:
  - model_name: gpt-5
    litellm_params:
      model: ${MODEL}
      api_key: os.environ/ANTHROPIC_API_KEY
      timeout: 120

allowed_routes:
  - /v1/chat/completions
  - /v1/completions
  - /v1/models
  - /v1/messages            # ✅ Anthropic unified
  - /anthropic/v1/messages  # ✅ Anthropic pass-through
  - /health
YAML

# --- Optional self-validate with Python + PyYAML (skips gracefully if unavailable) ---
PYTHON_BIN="$(command -v python3 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python || true)"
fi

if [[ -n "$PYTHON_BIN" ]]; then
  set +e
  "$PYTHON_BIN" - "$OUT_FILE" <<'PY'
import sys, pathlib
try:
    import yaml  # PyYAML
except Exception:
    print("ℹ️  Skipping YAML validation (PyYAML not installed).")
    sys.exit(0)

p = pathlib.Path(sys.argv[1])
yaml.safe_load(p.read_text())
print(f"✅ YAML OK: {p}")
PY
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    echo "❌ YAML validation failed"
    exit $rc
  fi
else
  echo "ℹ️  Skipping YAML validation (python not found)."
fi

echo "✅ Wrote: $OUT_FILE"
echo "   Host/Port : ${HOST}:${PORT}"
echo "   Alias     : gpt-5 → ${MODEL}"
echo "   CORS      : ${CORS_CSV}"
echo "   Note      : Runtime env must include LITELLM_MASTER_KEY and ANTHROPIC_API_KEY."