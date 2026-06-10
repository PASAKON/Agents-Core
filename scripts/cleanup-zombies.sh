#!/usr/bin/env bash
# scripts/cleanup-zombies.sh — remove stale lock sets (*.winid + siblings).
# A lock set is stale when its winid is not in iTerm's live window list.
# Siblings removed per stale set: .topic .lock .tty .watcher-pid (kills
# the watcher process too).
#
# Second pass: orphan siblings that never got a .winid (spawn died before
# the launcher booted, or the winid lookup failed) are removed once they
# are older than 24h and — for .lock/.watcher-pid — their pid is dead.
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

      rm -f "$f" "$LOCKS/$base.topic" "$LOCKS/$base.lock" "$LOCKS/$base.tty" "$LOCKS/$base.watcher-pid"
      removed=$((removed+1))
      ;;
  esac
done

orphans=0
now="$(date +%s)"
for f in "$LOCKS"/*.topic "$LOCKS"/*.lock "$LOCKS"/*.tty "$LOCKS"/*.watcher-pid; do
  [ -e "$f" ] || continue
  base="${f%.*}"
  [ -e "$base.winid" ] && continue  # has a lock set — pass 1 territory
  mtime="$(stat -f %m "$f" 2>/dev/null || echo "$now")"
  age=$(( now - mtime ))
  [ "$age" -ge 86400 ] || continue
  case "$f" in
    *.lock|*.watcher-pid)
      pid="$(tr -d '[:space:]' < "$f" 2>/dev/null || true)"
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        continue  # process still alive — not an orphan
      fi
      ;;
  esac
  rm -f "$f"
  orphans=$((orphans+1))
done

echo "cleanup-zombies: removed $removed stale lock set(s), $orphans orphan file(s)"
