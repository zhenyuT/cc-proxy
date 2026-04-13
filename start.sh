#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

EXTERNAL_UPSTREAM_BASE="${UPSTREAM_BASE:-}"
EXTERNAL_OPENAI_API_KEY="${OPENAI_API_KEY:-}"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

if [ -n "${EXTERNAL_UPSTREAM_BASE}" ]; then
  UPSTREAM_BASE="${EXTERNAL_UPSTREAM_BASE}"
fi

if [ -n "${EXTERNAL_OPENAI_API_KEY}" ]; then
  OPENAI_API_KEY="${EXTERNAL_OPENAI_API_KEY}"
fi

if [ -z "${UPSTREAM_BASE:-}" ]; then
  echo "UPSTREAM_BASE is required. Please set it in .env or your shell environment." >&2
  exit 1
fi

PROXY_HOST="${PROXY_HOST:-0.0.0.0}"
PROXY_PORT="${PROXY_PORT:-9000}"
DASHBOARD_HOST="${DASHBOARD_HOST:-0.0.0.0}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8888}"
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
UVICORN_RELOAD="${UVICORN_RELOAD:-1}"

UVICORN_ARGS=()
if [ "${UVICORN_RELOAD}" = "1" ]; then
  UVICORN_ARGS+=(--reload)
fi

cleanup() {
  if [ -n "${PROXY_PID:-}" ]; then
    kill "${PROXY_PID}" 2>/dev/null || true
  fi
  if [ -n "${DASHBOARD_PID:-}" ]; then
    kill "${DASHBOARD_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

"${PYTHON_BIN}" -m uvicorn proxy:app --host "${PROXY_HOST}" --port "${PROXY_PORT}" "${UVICORN_ARGS[@]}" &
PROXY_PID=$!

"${PYTHON_BIN}" -m uvicorn dashboard:app --host "${DASHBOARD_HOST}" --port "${DASHBOARD_PORT}" "${UVICORN_ARGS[@]}" &
DASHBOARD_PID=$!

wait -n "${PROXY_PID}" "${DASHBOARD_PID}"
