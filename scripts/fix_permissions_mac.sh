#!/usr/bin/env bash
set -euo pipefail

# Fix executable permissions for macOS launcher and shell scripts
# and remove quarantine attributes that block double‑click execution.

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo "Setting executable bits on .sh and .command scripts..."
chmod +x ./*.sh || true
chmod +x "Setup Mac.command" "Start App.command" "Uninstall Mac.command" || true

echo "Removing Apple quarantine attributes (may require password)..."
if command -v xattr >/dev/null 2>&1; then
  xattr -dr com.apple.quarantine "$HERE" || true
fi

echo "Done. If double‑click still fails, right‑click → Open once to approve."

