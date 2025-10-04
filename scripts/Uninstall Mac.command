#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/uninstall_mac.sh || true
echo ""
read -n 1 -s -r -p "Press any key to close..."
echo ""
