#!/usr/bin/env bash
set -euo pipefail

# Script to install a local Python + env using micromamba (no global changes)
# and install project requirements into it.

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
MAMBA_ROOT="$ROOT/.mamba"
ENV_PREFIX="$ROOT/.venv"
MAMBA_BIN_DIR="$MAMBA_ROOT/bin"
MICROMAMBA="$MAMBA_BIN_DIR/micromamba"

echo "Project root: $ROOT"

if [[ ! -x "$MICROMAMBA" ]]; then
  echo "Downloading micromamba..."
  mkdir -p "$MAMBA_ROOT" "$MAMBA_BIN_DIR"
  ARCH="$(uname -m)"
  case "$ARCH" in
    arm64) URL="https://micro.mamba.pm/api/micromamba/osx-arm64/latest" ;;
    x86_64) URL="https://micro.mamba.pm/api/micromamba/osx-64/latest" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
  esac
  TARBALL="$MAMBA_ROOT/micromamba.tar.bz2"
  curl -fL "${URL}" -o "$TARBALL"
  # Try extracting bin/micromamba into $MAMBA_ROOT
  tar -xjf "$TARBALL" -C "$MAMBA_ROOT" bin/micromamba 2>/dev/null || true
  # If not present under bin/, try without the bin/ prefix
  if [[ ! -f "$MAMBA_ROOT/bin/micromamba" ]]; then
    tar -xjf "$TARBALL" -C "$MAMBA_ROOT" micromamba 2>/dev/null || true
    if [[ -f "$MAMBA_ROOT/micromamba" ]]; then
      mv "$MAMBA_ROOT/micromamba" "$MAMBA_ROOT/bin/micromamba"
    fi
  fi
  if [[ ! -f "$MAMBA_ROOT/bin/micromamba" ]]; then
    # Last resort: find it anywhere in the tree
    FOUND="$(/usr/bin/find "$MAMBA_ROOT" -type f -name micromamba 2>/dev/null | head -n1 || true)"
    if [[ -n "$FOUND" ]]; then
      mv "$FOUND" "$MAMBA_ROOT/bin/micromamba"
    fi
  fi
  if [[ ! -f "$MAMBA_ROOT/bin/micromamba" ]]; then
    echo "Failed to extract micromamba binary. Please download manually from https://micro.mamba.pm/." >&2
    exit 1
  fi
  chmod +x "$MICROMAMBA"
  rm -f "$TARBALL"
fi

export MAMBA_ROOT_PREFIX="$MAMBA_ROOT"

if [[ ! -d "$ENV_PREFIX" ]]; then
  echo "Creating local env at $ENV_PREFIX..."
  "$MICROMAMBA" create -y -p "$ENV_PREFIX" python=3.9 pip
fi

echo "Installing Python packages into local env..."
"$MICROMAMBA" run -p "$ENV_PREFIX" python -m pip install -r "$ROOT/requirements.txt"

echo "Setup complete. To start the app:"
echo "  bash scripts/start_mac.sh"
