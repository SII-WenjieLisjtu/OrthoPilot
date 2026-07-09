#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${ORTHOPILOT_SERVICE_RUNTIME_DIR:-$REPO_ROOT/.service_runtime}"
LOG_DIR="$RUNTIME_DIR/logs"
PID_DIR="$RUNTIME_DIR/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

SERVICES=(
  "ehr|EHR_BASE_URL|http://localhost:9000|/health|EHR_START_COMMAND|"
  "similar-case|HOSPITAL_SIMILAR_URL|http://localhost:9999|/health|SIMILAR_CASE_START_COMMAND|"
  "knowledge-graph|KG_BASE_URL|http://localhost:8766|/health|KG_START_COMMAND|cd tool_plaza/bone_tools_api && exec python -m uvicorn tool_server:app --host 127.0.0.1 --port 8766"
  "medrag-translate|MEDRAG_TRANSLATE_BASE_URL|http://localhost:8888|/health|MEDRAG_TRANSLATE_START_COMMAND|"
  "medrag|MEDRAG_BASE_URL|http://localhost:8000|/health|MEDRAG_START_COMMAND|"
  "pmc-patients|PMC_PATIENTS_URL|http://localhost:9001|/health|PMC_PATIENTS_START_COMMAND|"
  "fathom-search|FATHOM_SANDBOX_URL|http://localhost:8904|/docs|FATHOM_SEARCH_START_COMMAND|"
  "qwen3-vllm|OPENAI_BASE_URL|http://localhost:8080/v1|/models|VLLM_START_COMMAND|"
)

service_field() {
  local record="$1"
  local index="$2"
  IFS='|' read -r name env_name default_url health_path command_env default_command <<< "$record"
  case "$index" in
    1) printf '%s' "$name" ;;
    2) printf '%s' "$env_name" ;;
    3) printf '%s' "$default_url" ;;
    4) printf '%s' "$health_path" ;;
    5) printf '%s' "$command_env" ;;
    6) printf '%s' "$default_command" ;;
  esac
}

health_url() {
  local record="$1"
  local env_name default_url health_path base_url
  env_name="$(service_field "$record" 2)"
  default_url="$(service_field "$record" 3)"
  health_path="$(service_field "$record" 4)"
  base_url="${!env_name:-$default_url}"
  printf '%s%s' "${base_url%/}" "$health_path"
}

is_healthy() {
  local url="$1"
  python - "$url" <<'PY' >/dev/null 2>&1
import sys
from urllib import request
url = sys.argv[1]
try:
    with request.urlopen(url, timeout=2) as response:
        raise SystemExit(0 if 200 <= response.status < 300 else 1)
except Exception:
    raise SystemExit(1)
PY
}

start_one() {
  local record="$1"
  local name command_env default_command command pid_file log_file
  name="$(service_field "$record" 1)"
  command_env="$(service_field "$record" 5)"
  default_command="$(service_field "$record" 6)"
  command="${!command_env:-$default_command}"
  pid_file="$PID_DIR/$name.pid"
  log_file="$LOG_DIR/$name.log"

  if [[ -z "$command" ]]; then
    echo "skip $name: set $command_env to start a local service for this public template"
    return 0
  fi
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "running $name: pid $(cat "$pid_file")"
    return 0
  fi

  echo "start $name: $command"
  (cd "$REPO_ROOT" && bash -c "$command" >"$log_file" 2>&1 & echo $! >"$pid_file")
}

stop_one() {
  local record="$1"
  local name pid_file
  name="$(service_field "$record" 1)"
  pid_file="$PID_DIR/$name.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    kill "$(cat "$pid_file")" 2>/dev/null || true
    echo "stop $name: pid $(cat "$pid_file")"
  else
    echo "not running $name"
  fi
  if [[ "$name" == "knowledge-graph" ]]; then
    for child_pid in $(pgrep -f "[u]vicorn tool_server:app --host 127.0.0.1 --port 8766" 2>/dev/null || true); do
      kill "$child_pid" 2>/dev/null || true
    done
    for _ in $(seq 1 5); do
      if ! pgrep -f "[u]vicorn tool_server:app --host 127.0.0.1 --port 8766" >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
  fi
  rm -f "$pid_file"
}

status_one() {
  local record="$1"
  local name url pid_state health_state pid_file
  name="$(service_field "$record" 1)"
  url="$(health_url "$record")"
  pid_file="$PID_DIR/$name.pid"
  pid_state="not-started"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    pid_state="pid $(cat "$pid_file")"
  fi
  if is_healthy "$url"; then
    health_state="healthy"
  else
    health_state="unreachable"
  fi
  printf '%-18s %-14s %s\n' "$name" "$pid_state" "$url ($health_state)"
}

usage() {
  echo "Usage: bash tool_plaza/start_all_services.sh [start|stop|status]"
  echo "Manifest: tool_plaza/service_manifest.json"
}

command="${1:-status}"
case "$command" in
  start)
    for service in "${SERVICES[@]}"; do
      start_one "$service"
    done
    ;;
  stop)
    for service in "${SERVICES[@]}"; do
      stop_one "$service"
    done
    ;;
  status)
    for service in "${SERVICES[@]}"; do
      status_one "$service"
    done
    ;;
  *)
    usage
    exit 2
    ;;
esac
