#!/usr/bin/env bash
# scripts/cleanup-zombies.sh — remove stale *.winid lock files only.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKS="$ROOT/state/locks"
live="$(osascript -e 'tell application "iTerm2" to return id of windows' | tr -d ' ')"
removed=0
for f in "$LOCKS"/*.winid; do
  [ -e "$f" ] || continue
  wid="$(cat "$f")"
  case ",$live," in
    *",$wid,"*) ;;
    *) rm -f "$f"; removed=$((removed+1));;
  esac
done
echo "cleanup-zombies: removed $removed stale lock file(s)"
