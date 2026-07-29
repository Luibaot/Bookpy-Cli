#!/usr/bin/env bash
set -euo pipefail

if command -v brew >/dev/null 2>&1; then
  echo "Homebrew detected. Install the published formula with:"
  echo "  brew install <tap>/bookpy-cli"
fi

if command -v pipx >/dev/null 2>&1; then
  pipx install bookpy-cli
elif command -v uv >/dev/null 2>&1; then
  uv tool install bookpy-cli
else
  read -r -p "Install pipx with Homebrew? [y/N] " answer
  if [[ "$answer" =~ ^[Yy]$ ]] && command -v brew >/dev/null 2>&1; then
    brew install pipx
    pipx ensurepath
    pipx install bookpy-cli
  else
    echo "Install pipx or uv, then run: pipx install bookpy-cli"
    exit 1
  fi
fi

bookpy-cli doctor
echo "\nReady. Launch it with: bookpy-cli"
