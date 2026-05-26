#!/usr/bin/env bash
# scripts/cleanup-zombies.sh — remove stale lock sets (*.winid + siblings).
# A lock set is stale when its winid is not in iTerm's live window list.
# Siblings removed per stale set: .topic  .lock  .watcher-pid (kills watcher too).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKS="$ROOT/state/locks"
live="$(osascript -e 'tell application "iTerm2" to return id of windows' 2>/dev/null | tr -d ' ')"
removed=0
for f in "$LOCKS"/*.winid; do
  [ -e "$f" ] || continue
  wid="$(cat "$f")"
  case ",$live," in
    *",$wid,"*) ;;  # live — leave it alone
    *)
      base="${f%.winid}"
      base="${base##*/}"

      pid_file="$LOCKS/$base.watcher-pid"
      if [ -f "$pid_file" ]; then
        watcher_pid="$(tr -d '[:space:]' < "$pid_file" 2>/dev/null || true)"
        if [ -n "$watcher_pid" ] && kill -0 "$watcher_pid" 2>/dev/null; then
          kill "$watcher_pid" 2>/dev/null || true
        fi
      fi

      rm -f "$f" "$LOCKS/$base.topic" "$LOCKS/$base.lock" "$LOCKS/$base.watcher-pid"
      removed=$((removed+1))
      ;;
  esac
done
echo "cleanup-zombies: removed $removed stale lock set(s)"
