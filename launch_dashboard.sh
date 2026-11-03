#!/bin/zsh
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Missing Python environment. Run ./install_mac.sh first.'
  exit 1
fi
exec .venv/bin/python -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501 --server.headless false --browser.gatherUsageStats false
