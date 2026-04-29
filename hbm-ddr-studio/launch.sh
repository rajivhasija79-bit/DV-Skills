#!/usr/bin/env bash
# HBM-DDR Studio launcher: starts FastAPI backend (8000) + Vite frontend (5173).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(
  cd "$ROOT/backend"
  if [ -d .venv ]; then source .venv/bin/activate; fi
  exec uvicorn app.main:app --reload --port 8000
) &

(
  cd "$ROOT/frontend"
  exec npm run dev
) &

wait
