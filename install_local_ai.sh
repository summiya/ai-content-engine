#!/bin/zsh
set -e
cd "$(dirname "$0")"
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "This local preset requires an Apple Silicon Mac."
  exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "Missing uv package manager."
  echo "Install uv with Homebrew: brew install uv"
  echo "Or see https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi
uv tool install --upgrade mflux
if ! command -v mflux-generate-flux2 >/dev/null 2>&1; then
  echo "MFLUX installed, but its command isn't on PATH yet."
  echo "Run: uv tool update-shell"
  echo "Then restart Terminal."
  exit 0
fi
echo "MFLUX installed. First generation will download FLUX.2 Klein 4B model files."
echo "Edit .env: IMAGE_PROVIDER=local, DAILY_COUNT=1, AUTO_PUBLISH=false"
echo "Then run: .venv/bin/python content_engine.py daily"
