#!/bin/bash
# Render EP57 in <=9s windows, one fresh process each, stop on first failure.
# CTO final instruction, task-501f1d89, 2026-09-24 03:00.
set -u
BASE=/Users/gob/MoonieXHQ/Work/task-501f1d89/tmp
OUT=/Users/gob/MoonieXHQ/Work/task-501f1d89/out/parts
SKILL=/Users/gob/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__video_editor__task-501f1d89/.claude/skills/blackliquidity-cut/template
mkdir -p "$OUT"

n=0
while read -r ws we <&3; do
  [ -z "$ws" ] && continue
  n=$((n+1))
  wid=$(printf "w%02d" "$n")
  D="$BASE/$wid"
  if [ -f "$OUT/${wid}.mp4" ]; then
    echo "=== $wid  ${ws}-${we}s === already rendered, skipping"
    continue
  fi
  echo "=== $wid  ${ws}-${we}s ==="

  mp=$(memory_pressure | tail -1 | grep -oE '[0-9]+%' | grep -oE '[0-9]+')
  echo "memory_pressure free%: $mp"
  if [ -z "$mp" ] || [ "$mp" -lt 25 ]; then
    echo "STOP: memory_pressure ${mp}% < 25% before $wid even started"
    exit 2
  fi

  rm -rf "$D"
  mkdir -p "$D"
  cp "$SKILL/index.html" "$D/index.html"
  cp "$SKILL/hyperframes.json" "$D/hyperframes.json"
  cp "$SKILL/package.json" "$D/package.json"
  cp -R "$SKILL/assets" "$D/assets"
  ln -sf "$BASE/cut/media" "$D/media"

  python3 "$BASE/build_cut.py" "$ws" "$we" || { echo "STOP: build_cut.py failed for $wid"; exit 3; }
  pieces=$(python3 -c "print('$BASE/cut_pieces-%g-%g.json' % ($ws, $we))")
  python3 "$BASE/assemble.py" "$D/index.html" "$pieces" "$ws" || { echo "STOP: assemble.py failed for $wid"; exit 3; }

  (cd "$D" && npm run check 2>&1 | tail -25)

  (cd "$D" && npx --yes hyperframes@0.8.40 render -o "$OUT/${wid}.mp4" 2>&1 | tail -40) > "$BASE/${wid}.renderlog" 2>&1
  if grep -q "Render complete" "$BASE/${wid}.renderlog" && [ -f "$OUT/${wid}.mp4" ]; then
    echo "$wid OK"
    tail -3 "$BASE/${wid}.renderlog"
  else
    echo "STOP: $wid FAILED. memory_pressure at start was ${mp}%. Tail of renderlog:"
    tail -20 "$BASE/${wid}.renderlog"
    mp2=$(memory_pressure | tail -1)
    echo "memory_pressure now: $mp2"
    exit 4
  fi
done 3< "$BASE/windows.txt"

echo "ALL WINDOWS RENDERED OK ($n total)"
