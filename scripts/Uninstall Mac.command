#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec bash scripts/uninstall_mac.sh

