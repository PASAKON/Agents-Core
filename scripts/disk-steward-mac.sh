#!/usr/bin/env bash
# User launchd runner; requires the P1 steward and machine contract.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || { echo "disk-steward-mac: missing repo .venv/bin/python (requires PyYAML)" >&2; exit 1; }
# shlex.quote prevents paths in the contract from becoming shell commands.
CONFIG="$("$PY" - "$ROOT" <<'PY'
import pathlib, shlex, sys
try:
    import yaml
    data = yaml.safe_load((pathlib.Path(sys.argv[1]) / 'config/machine-contract.yaml').read_text())
    row = data['machines']['mac']
    values = {}
    for key, env in [('home', 'HOME'), ('hq', 'MOONIEX_HQ'), ('claude_config_dir', 'CLAUDE_CONFIG_DIR')]:
        value = row[key]
        if not isinstance(value, str) or not value.startswith('/') or '\n' in value:
            raise ValueError('machines.mac.' + key + ' must be an absolute path')
        values[env] = value
    if row.get('drive_leg') != 'rest_work_archive':
        raise ValueError('machines.mac.drive_leg must be rest_work_archive')
    for env, value in values.items():
        print('export ' + env + '=' + shlex.quote(value))
except Exception as exc:
    sys.exit('disk-steward-mac: invalid machine-contract.yaml; requires machines.mac with home/hq/claude_config_dir and REST drive_leg: ' + str(exc))
PY
)"
eval "$CONFIG"
export ORG_HOST=mac
export PATH="${PATH:-/usr/bin:/bin:/usr/sbin:/sbin}:/opt/homebrew/bin:/usr/local/bin:/Applications/Tailscale.app/Contents/MacOS"
[[ -f tools/disk_steward.py ]] || { echo "disk-steward-mac: missing tools/disk_steward.py; merge P1 first" >&2; exit 1; }
mkdir -p state/storage
# Stream output through a bounded rotating log, preserving the command's failure
# through pipefail. One 5 MiB backup is retained; no GNU/macOS stat differences.
bash scripts/hub/org-python.sh tools/disk_steward.py tick --host mac "$@" 2>&1 | "$PY" -c '
import logging, logging.handlers, sys
handler = logging.handlers.RotatingFileHandler(sys.argv[1], maxBytes=5*1024*1024, backupCount=1)
logger = logging.getLogger("disk-steward-mac")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
for line in sys.stdin:
    logger.info(line.rstrip("\n"))
' "$ROOT/state/storage/steward-mac.log"
