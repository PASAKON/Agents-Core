#!/usr/bin/env bash
# Render and register a GUI user LaunchAgent. --dry-run writes nothing.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL=com.mooniex.disk-steward
DRY=0
UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    *) echo "usage: $0 [--dry-run] [--uninstall]" >&2; exit 2 ;;
  esac
done
: "${HOME:?HOME must name the installing user home}"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"
if [[ "$DRY" == 0 ]]; then
  [[ "$(id -u)" != 0 ]] || { echo "Refusing root: run as the Mac GUI user, without sudo" >&2; exit 1; }
  [[ "$(uname -s)" == Darwin ]] || { echo "Installation requires macOS" >&2; exit 1; }
fi
rollback() {
  echo 'launchctl bootout gui/$(id -u)/com.mooniex.disk-steward && rm ~/Library/LaunchAgents/com.mooniex.disk-steward.plist'
}
if [[ "$UNINSTALL" == 1 ]]; then
  if [[ "$DRY" == 1 ]]; then
    printf 'launchctl bootout %q\nrm -f %q\n' "$DOMAIN/$LABEL" "$PLIST"
  else
    if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
      launchctl bootout "$DOMAIN/$LABEL"
    fi
    rm -f "$PLIST"
  fi
  exit 0
fi
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"
RENDERED="$("$PY" - "$ROOT" "$HOME" <<'PY'
import pathlib, plistlib, sys
root, home = sys.argv[1:]
data = plistlib.loads((pathlib.Path(root) / 'deploy/launchd/com.mooniex.disk-steward.plist').read_bytes())
def render(value):
    if isinstance(value, str):
        return value.replace('@ROOT@', root).replace('@HOME@', home)
    if isinstance(value, list):
        return [render(v) for v in value]
    if isinstance(value, dict):
        return {k: render(v) for k, v in value.items()}
    return value
sys.stdout.write(plistlib.dumps(render(data)).decode())
PY
)"
if [[ "$DRY" == 1 ]]; then
  printf '%s\n' "$RENDERED"
  printf 'mkdir -p %q\n' "$(dirname "$PLIST")"
  printf 'printf %%s %q > %q\n' "$RENDERED" "$PLIST"
  printf 'if launchctl print %q >/dev/null 2>&1; then launchctl bootout %q; fi\n' "$DOMAIN/$LABEL" "$DOMAIN/$LABEL"
  printf 'launchctl bootstrap %q %q\n' "$DOMAIN" "$PLIST"
else
  [[ -x "$ROOT/.venv/bin/python" && -f "$ROOT/tools/disk_steward.py" ]] || {
    echo 'Missing repo venv or P1 tools/disk_steward.py; merge P1 and prepare the Mac venv first' >&2; exit 1;
  }
  mkdir -p "$(dirname "$PLIST")"
  if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
    launchctl bootout "$DOMAIN/$LABEL"
  fi
  printf '%s\n' "$RENDERED" > "$PLIST"
  launchctl bootstrap "$DOMAIN" "$PLIST"
fi
echo 'Rollback:'
rollback
