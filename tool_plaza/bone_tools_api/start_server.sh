#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8766}"
WORKERS="${WORKERS:-1}"
LOG_DIR="${LOG_DIR:-${SCRIPT_DIR}/logs}"

mkdir -p "${LOG_DIR}"

printf '%s\n' "Starting Tool Plaza API server"
printf 'Host: %s\n' "${HOST}"
printf 'Port: %s\n' "${PORT}"
printf 'Workers: %s\n' "${WORKERS}"
printf 'Logs: %s\n' "${LOG_DIR}"
printf 'API URL: http://%s:%s\n' "${HOST}" "${PORT}"

if [[ "${WORKERS}" == "1" ]]; then
  exec uvicorn tool_server:app --host "${HOST}" --port "${PORT}"
fi

exec uvicorn tool_server:app --host "${HOST}" --port "${PORT}" --workers "${WORKERS}"
