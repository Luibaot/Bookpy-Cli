#!/usr/bin/env bash
set -euo pipefail

if command -v pipx >/dev/null 2>&1; then
  pipx uninstall bookpy-cli || true
fi
if command -v uv >/dev/null 2>&1; then
  uv tool uninstall bookpy-cli || true
fi
echo "Application removed. Your config and library files were left untouched."
