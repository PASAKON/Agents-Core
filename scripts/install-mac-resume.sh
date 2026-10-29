#!/usr/bin/env bash
# Render the checked-in template, then load it in the current user's GUI domain.
set -euo pipefail
repo=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
if [ $# -ne 0 ]; then
  [ $# -eq 2 ] && [ "$1" = '--repo' ] || { echo 'usage: install-mac-resume.sh [--repo PATH]' >&2; exit 2; }
  repo=$2
fi
[[ "$repo" = /* ]] || exit 2
destination="$HOME/Library/LaunchAgents/com.mooniex.org-resume.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$repo/state/restart"
python3 - "$repo" "$destination" <<'PY'
import pathlib
import plistlib
import sys
repo, destination = sys.argv[1:]
source = pathlib.Path(repo, 'deploy/launchd/com.mooniex.org-resume.plist')
data = plistlib.loads(source.read_bytes())
def render(value):
    if isinstance(value, str):
        return value.replace('__REPO__', repo)
    if isinstance(value, list):
        return [render(item) for item in value]
    if isinstance(value, dict):
        return {key: render(item) for key, item in value.items()}
    return value
pathlib.Path(destination).write_bytes(plistlib.dumps(render(data)))
PY
launchctl bootstrap "gui/$(id -u)" "$destination"
