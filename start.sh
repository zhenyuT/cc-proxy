#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

if [ -z "${UPSTREAM_BASE:-}" ]; then
  echo "UPSTREAM_BASE is required. Please set it in .env or your shell environment." >&2
  exit 1
fi

.venv/bin/python -m uvicorn proxy:app --host 0.0.0.0 --port 9000 --reload
