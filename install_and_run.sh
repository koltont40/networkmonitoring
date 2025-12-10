#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--help]

Creates a local Python virtual environment (if missing), installs dependencies,
loads environment variables from .env when present, and launches the FastAPI
server with uvicorn.

Environment overrides:
  PYTHON       Python interpreter to use (default: python3)
  VENV_DIR     Virtualenv path (default: .venv in repo root)
  APP_MODULE   Uvicorn app import (default: app.main:app)
  UVICORN_OPTS Extra uvicorn CLI args (default: "--host 0.0.0.0 --port 8000")
USAGE
}

if [[ ${1-} == "--help" ]]; then
  usage
  exit 0
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-$REPO_DIR/.venv}"
APP_MODULE="${APP_MODULE:-app.main:app}"
UVICORN_OPTS="${UVICORN_OPTS:---host 0.0.0.0 --port 8000}"

printf "\n[1/4] Ensuring virtual environment at %s\\n" "$VENV_DIR"
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

printf "[2/4] Upgrading pip and installing requirements\\n"
pip install --upgrade pip >/dev/null
pip install -r "$REPO_DIR/requirements.txt"

if [[ -f "$REPO_DIR/.env" ]]; then
  printf "[3/4] Loading environment from .env\\n"
  # shellcheck disable=SC1091
  set -a
  source "$REPO_DIR/.env"
  set +a
else
  printf "[3/4] No .env file found; proceeding with current environment\\n"
fi

printf "[4/4] Starting uvicorn (%s)\\n\n" "$UVICORN_OPTS"
exec uvicorn "$APP_MODULE" $UVICORN_OPTS
