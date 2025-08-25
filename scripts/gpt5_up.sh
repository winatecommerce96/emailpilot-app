#!/usr/bin/env bash
# scripts/gpt5_up.sh — One-command AUTH-enabled startup for GPT‑5 via LiteLLM + Claude Code
# Usage:
#   scripts/gpt5_up.sh init                 # create .env (prompts), write config, ensure helper scripts
#   scripts/gpt5_up.sh start [profile]      # start gateway (bg) then launch Claude (heavy|standard|budget|opus|native-haiku)
#   scripts/gpt5_up.sh start-gateway        # start only the gateway (no Claude)
#   scripts/gpt5_up.sh stop                 # stop gateway
#   scripts/gpt5_up.sh status               # show pid/port and last log lines
#   scripts/gpt5_up.sh logs                 # tail logs
#   scripts/gpt5_up.sh doctor               # health + probe curls
#
# Profiles:
#   heavy (default)  -> gpt-5 main, haiku fast (mapped to gpt-5-mini)
#   standard         -> Sonnet native + Haiku native (requires ANTHROPIC_API_KEY mapped if using native)
#   budget           -> mini everywhere
#   opus             -> Opus native + Haiku native
#   native-haiku     -> Haiku native everywhere
#
set -euo pipefail

ROOT="${PROJECT_ROOT:-$(pwd)}"
ENV_FILE="$ROOT/.env"
SCRIPTS_DIR="$ROOT/scripts"
CFG_DIR="$ROOT/config/gpt5"
CFG_FILE="$CFG_DIR/soft.yaml"
VENV="$ROOT/.gpt5-soft"
PORT="${PORT:-4000}"
HOST="127.0.0.1"
PIDFILE="$ROOT/.gpt5-soft.pid"
LOGFILE="$ROOT/.gpt5-soft.log"

START_SOFT="$SCRIPTS_DIR/start_gpt5_soft.sh"
CLAUDE_PROFILES="$SCRIPTS_DIR/claude_profiles.sh"

mkdir -p "$SCRIPTS_DIR" "$CFG_DIR"

mask() { # mask long secrets for logs
  local s="${1:-}"; if [ -z "$s" ]; then echo "<unset>"; return; fi
  local n=${#s}; if (( n <= 8 )); then echo "******"; else echo "${s:0:4}…${s: -4}"; fi
}

write_soft_yaml_if_missing() {
  if [[ -f "$CFG_FILE" ]]; then return; fi
  cat > "$CFG_FILE" <<'YAML'
general_settings:
  telemetry: false
  master_key: ""  # set by gpt5_up.sh when using auth

proxy_settings:
  host: 127.0.0.1
  port: 4000
  cors: ["*"]

litellm_settings:
  set_verbose: true
  drop_params: true
  timeout: 120
  num_retries: 3

model_list:
  # ----- OpenAI GPT-5 (heavy) -----
  - model_name: gpt-5
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY
      timeout: 120

  - model_name: sonnet
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-3-5-sonnet-20240620
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-3-5-sonnet-latest
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-sonnet-4-20250514
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-sonnet-4-latest
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-3-opus-20240229
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-3-opus-latest
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY

  # ----- OpenAI GPT-5-mini (budget/fast) -----
  - model_name: gpt-5-mini
    litellm_params:
      model: openai/gpt-5-mini
      api_key: os.environ/OPENAI_API_KEY

  - model_name: haiku
    litellm_params:
      model: openai/gpt-5-mini
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-3-5-haiku-20241022
    litellm_params:
      model: openai/gpt-5-mini
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-3-5-haiku-latest
    litellm_params:
      model: openai/gpt-5-mini
      api_key: os.environ/OPENAI_API_KEY
YAML
}

ensure_start_soft() {
  if [[ -x "$START_SOFT" ]]; then return; fi
  cat > "$START_SOFT" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ROOT="${PROJECT_ROOT:-$(pwd)}"
CFG_DIR="$ROOT/config/gpt5"
CFG_FILE="$CFG_DIR/soft.yaml"
VENV="$ROOT/.gpt5-soft"
HOST="127.0.0.1"
PORT="4000"

mkdir -p "$CFG_DIR"

# load .env
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then set -a; source "$ENV_FILE"; set +a; fi
: "${OPENAI_API_KEY:?ERROR: OPENAI_API_KEY not set. Put it in .env or export it.}"

# kill anything on the port
lsof -ti tcp:$PORT 2>/dev/null | xargs -r kill -9 || true

python3 -m venv "$VENV" 2>/dev/null || true
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip -q install -U pip "litellm[proxy]"

EXPECT="<none>"
if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then
  EXPECT="Bearer ${LITELLM_MASTER_KEY:0:4}…${LITELLM_MASTER_KEY: -4}"
fi
echo "🔐 Expect header: Authorization: ${EXPECT}"
echo "📝 Config: $CFG_FILE"
echo "🚀 LiteLLM → http://$HOST:$PORT (OpenAI backend)"

exec litellm --host "$HOST" --port "$PORT" --config "$CFG_FILE"
SH
  chmod +x "$START_SOFT"
}

ensure_profiles() {
  if [[ -x "$CLAUDE_PROFILES" ]]; then return; fi
  cat > "$CLAUDE_PROFILES" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
PROFILE="${1:-heavy}"; shift || true
ROOT="${PROJECT_ROOT:-$(pwd)}"
ENV_FILE="$ROOT/.env"; [[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }
BASE="http://127.0.0.1:4000"
export ANTHROPIC_BASE_URL="$BASE"
export ANTHROPIC_API_BASE="$BASE"
if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then
  export ANTHROPIC_AUTH_TOKEN="Bearer ${LITELLM_MASTER_KEY}"
else
  unset ANTHROPIC_AUTH_TOKEN
fi
export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-4096}"
case "$PROFILE" in
  heavy)        export ANTHROPIC_MODEL="gpt-5"; export ANTHROPIC_SMALL_FAST_MODEL="haiku" ;;
  standard)     export ANTHROPIC_MODEL="claude-3-5-sonnet-20240620"; export ANTHROPIC_SMALL_FAST_MODEL="claude-3-5-haiku-20241022" ;;
  budget)       export ANTHROPIC_MODEL="haiku"; export ANTHROPIC_SMALL_FAST_MODEL="haiku" ;;
  opus)         export ANTHROPIC_MODEL="claude-3-opus-20240229"; export ANTHROPIC_SMALL_FAST_MODEL="claude-3-5-haiku-20241022" ;;
  native-haiku) export ANTHROPIC_MODEL="claude-3-5-haiku-20241022"; export ANTHROPIC_SMALL_FAST_MODEL="claude-3-5-haiku-20241022" ;;
  *) echo "Unknown profile: $PROFILE"; echo "Valid: heavy|standard|budget|opus|native-haiku"; exit 2 ;;
esac
echo "📎 Profile: $PROFILE"
echo "  Base URL: $ANTHROPIC_BASE_URL"
echo "  Model:    $ANTHROPIC_MODEL"
echo "  Fast:     $ANTHROPIC_SMALL_FAST_MODEL"
if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then echo "  Auth:     Bearer (gateway)"; else echo "  Auth:     none"; fi
exec npx -y "npm:@anthropic-ai/claude-code@${CLAUDE_CLI_VERSION:-1.0.61}" "$@"
SH
  chmod +x "$CLAUDE_PROFILES"
}

patch_master_key_in_yaml() {
  local key="$1"
  python3 - "$CFG_FILE" "$key" <<'PY'
import sys, re, io
path, key = sys.argv[1], sys.argv[2]
with io.open(path, 'r', encoding='utf-8') as f:
    y = f.read()
# Replace the master_key line value with a quoted literal, keep indentation
y = re.sub(r'(?m)^(\\s*master_key:\\s*).*$',
           r'\\1"{}"'.format(key.replace('\\', '\\\\').replace('"', '\\"')),
           y)
with io.open(path, 'w', encoding='utf-8') as f:
    f.write(y)
print("✅ YAML master_key updated")
PY
}

ensure_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "# Local secrets for GPT-5 gateway" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
  fi
  if ! grep -q '^OPENAI_API_KEY=' "$ENV_FILE" 2>/dev/null; then
    read -r -s -p "Enter OPENAI_API_KEY: " OPENAI_API_KEY_INPUT; echo
    echo "OPENAI_API_KEY=$OPENAI_API_KEY_INPUT" >> "$ENV_FILE"
  fi
  if ! grep -q '^LITELLM_MASTER_KEY=' "$ENV_FILE" 2>/dev/null; then
    read -r -s -p "Set LITELLM_MASTER_KEY (gateway auth token): " LITELLM_MASTER_KEY_INPUT; echo
    echo "LITELLM_MASTER_KEY=$LITELLM_MASTER_KEY_INPUT" >> "$ENV_FILE"
  fi
  echo "🔐 .env ready → OPENAI_API_KEY=$(mask "$(grep -E '^OPENAI_API_KEY=' "$ENV_FILE" | cut -d= -f2-)")  ·  LITELLM_MASTER_KEY=$(mask "$(grep -E '^LITELLM_MASTER_KEY=' "$ENV_FILE" | cut -d= -f2-)")"
}

start_gateway_bg() {
  set -a; source "$ENV_FILE"; set +a
  : "${OPENAI_API_KEY:?}"; : "${LITELLM_MASTER_KEY:?}"
  patch_master_key_in_yaml "$LITELLM_MASTER_KEY"
  # Kill if running
  lsof -ti tcp:$PORT 2>/dev/null | xargs -r kill -9 || true
  # Start and log
  echo "🟢 Starting gateway on http://$HOST:$PORT … logs → $LOGFILE"
  : > "$LOGFILE"
  nohup "$START_SOFT" >"$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  sleep 1
  if ! lsof -i tcp:$PORT >/dev/null 2>&1; then
    echo "❌ Port $PORT not listening. See $LOGFILE"; exit 1
  fi
  echo "🚀 Gateway started (pid $(cat "$PIDFILE"))"
}

stop_gateway() {
  if [[ -f "$PIDFILE" ]]; then
    kill "$(cat "$PIDFILE")" 2>/dev/null || true
    rm -f "$PIDFILE"
  fi
  lsof -ti tcp:$PORT 2>/dev/null | xargs -r kill -9 || true
  echo "🛑 Gateway stopped"
}

status() {
  echo "📊 Status:"
  if lsof -i tcp:$PORT >/dev/null 2>&1; then
    echo "  Port: $PORT (LISTEN)"
  else
    echo "  Port: $PORT (not listening)"
  fi
  if [[ -f "$PIDFILE" ]] && ps -p "$(cat "$PIDFILE")" >/dev/null 2>&1; then
    echo "  PID: $(cat "$PIDFILE")"
  else
    echo "  PID: <none>"
  fi
  echo "— Last 20 log lines —"
  tail -n 20 "$LOGFILE" 2>/dev/null || echo "(no logs yet)"
}

logs() {
  echo "📜 Tailing $LOGFILE (Ctrl+C to stop)"
  tail -f "$LOGFILE"
}

doctor() {
  set -e
  echo "🔎 Health check:"
  curl -s "http://$HOST:$PORT/health" || echo "(no /health endpoint)"
  echo
  set -a; source "$ENV_FILE" 2>/dev/null || true; set +a
  AUTH_HDR=(-H "Authorization: Bearer $LITELLM_MASTER_KEY")
  echo "🔎 Probe gpt-5:"
  curl -s "http://$HOST:$PORT/v1/messages" -H "Content-Type: application/json" "${AUTH_HDR[@]}" \
    -d '{"model":"gpt-5","max_tokens":8,"messages":[{"role":"user","content":"ping"}]}' | head -c 300; echo
  echo "🔎 Probe haiku:"
  curl -s "http://$HOST:$PORT/v1/messages" -H "Content-Type: application/json" "${AUTH_HDR[@]}" \
    -d '{"model":"haiku","max_tokens":8,"messages":[{"role":"user","content":"pong"}]}' | head -c 300; echo
}

cmd="${1:-}"; shift || true
case "$cmd" in
  init)
    write_soft_yaml_if_missing
    ensure_start_soft
    ensure_profiles
    ensure_env
    echo "✅ Init complete. Next: scripts/gpt5_up.sh start"
    ;;
  start)
    profile="${1:-heavy}"
    write_soft_yaml_if_missing
    ensure_start_soft
    ensure_profiles
    ensure_env
    start_gateway_bg
    exec "$CLAUDE_PROFILES" "$profile"
    ;;
  start-gateway)
    write_soft_yaml_if_missing
    ensure_start_soft
    ensure_env
    start_gateway_bg
    ;;
  stop) stop_gateway ;;
  status) status ;;
  logs) logs ;;
  doctor) doctor ;;
  *)
    echo "Usage:"
    echo "  $0 init                 # create .env (prompts), write config, ensure helper scripts"
    echo "  $0 start [profile]      # start gateway (bg) then launch Claude (heavy|standard|budget|opus|native-haiku)"
    echo "  $0 start-gateway        # start only the gateway"
    echo "  $0 stop                 # stop gateway"
    echo "  $0 status               # show pid/port and last log lines"
    echo "  $0 logs                 # tail logs"
    echo "  $0 doctor               # health + probe curls"
    exit 2
    ;;
esac
