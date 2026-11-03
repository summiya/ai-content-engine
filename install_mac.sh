#!/bin/zsh
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then
  echo 'Python 3 not found. Install Python 3.11+ from https://www.python.org/downloads/macos/'
  exit 1
fi
python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit('Please install Python 3.11 or newer.')
PY
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; fi
.venv/bin/python content_engine.py demo
.venv/bin/python content_engine.py doctor
echo 'Installation finished.'
echo 'Next: edit .env, test with .venv/bin/python content_engine.py daily, and review output/.'
