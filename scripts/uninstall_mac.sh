#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

echo "This will remove the local Python environment in:"
echo "  $ROOT/.venv"
echo "  $ROOT/.mamba"
read -p "Proceed? (y/N): " ans
ans=${ans:-N}
if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
  echo "Aborted."
  exit 1
fi

rm -rf "$ROOT/.venv" "$ROOT/.mamba"
echo "Local environment removed."

