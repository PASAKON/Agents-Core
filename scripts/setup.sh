#!/usr/bin/env bash
# One-shot setup: venv, deps, db init.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
  echo "[setup] venv created"
fi

source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
echo "[setup] deps installed"

python -m lib.db init
echo "[setup] db initialized"

echo
echo "Done. Next:"
echo "  source $(pwd)/.venv/bin/activate"
echo "  source $(pwd)/scripts/aliases.sh   # optional aliases"
echo "  python main.py 'your request here'"
echo "  python dashboard.py               # in another terminal"
