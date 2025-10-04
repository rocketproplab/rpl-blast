#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
MAMBA_ROOT="$ROOT/.mamba"
ENV_PREFIX="$ROOT/.venv"
MICROMAMBA="$MAMBA_ROOT/bin/micromamba"

export MAMBA_ROOT_PREFIX="$MAMBA_ROOT"

if [[ ! -x "$MICROMAMBA" ]]; then
  echo "micromamba not found. Run scripts/setup_mac.sh first."
  exit 1
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
echo "Starting BLAST FastAPI at http://$HOST:$PORT ..."
exec "$MICROMAMBA" run -p "$ENV_PREFIX" uvicorn backend.app.main:app --host "$HOST" --port "$PORT"

