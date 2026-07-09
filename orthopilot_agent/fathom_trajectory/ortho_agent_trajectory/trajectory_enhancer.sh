#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

if [[ -z "${INPUT_DIR:-}" ]]; then
 printf '%s\n' "ERROR: INPUT_DIR must be set to an existing trajectory input directory." >&2
 printf '%s\n' "Example: INPUT_DIR=data/input ${0}" >&2
 exit 2
fi

if [[ ! -d "${INPUT_DIR}" ]]; then
 printf 'ERROR: INPUT_DIR does not exist or is not a directory: %s\n' "${INPUT_DIR}" >&2
 exit 2
fi

OUTPUT_DIR="${OUTPUT_DIR:-${SCRIPT_DIR}/outputs}"
OUTPUT_JSONL="${OUTPUT_JSONL:-${OUTPUT_DIR}/search_r1_example.jsonl}"
MODEL_URL="${MODEL_URL:-http://localhost:8000}"
EXECUTORS="${EXECUTORS:-http://localhost:8000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$(dirname "${OUTPUT_JSONL}")"

printf '%s\n' "Running trajectory enhancer"
printf 'Repository root: %s\n' "${REPO_ROOT}"
printf 'Input directory: %s\n' "${INPUT_DIR}"
printf 'Output JSONL: %s\n' "${OUTPUT_JSONL}"
printf 'Model URL: %s\n' "${MODEL_URL}"
printf 'Executors: %s\n' "${EXECUTORS}"

exec "${PYTHON_BIN}" "${SCRIPT_DIR}/trajectory_enhancer_r1.py" \
 --distill-with-gt \
 --input-dir "${INPUT_DIR}" \
 --output-jsonl "${OUTPUT_JSONL}" \
 --model-url "${MODEL_URL}" \
 --executors "${EXECUTORS}"
