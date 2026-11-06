#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -x "${PROJECT_ROOT}/.venv/bin/python3" ]]; then
  PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python3"
elif [[ -x "${PROJECT_ROOT}/../proj_cdc_mig/.venv/bin/python3" ]]; then
  PYTHON_BIN="${PROJECT_ROOT}/../proj_cdc_mig/.venv/bin/python3"
elif [[ -x "${PROJECT_ROOT}/../proj_brain_for_home/.venv/bin/python3" ]]; then
  PYTHON_BIN="${PROJECT_ROOT}/../proj_brain_for_home/.venv/bin/python3"
else
  PYTHON_BIN="python3"
fi

export PATH="${HOME}/.local/bin:${PATH}"
PORT="${PORT:-8500}"
exec "$PYTHON_BIN" -m uvicorn app.backend.main:app --host 0.0.0.0 --port "$PORT" --reload --reload-dir app/backend --reload-dir scripts
