#!/bin/bash
# usage: render_v1.sh A|B [segNN ...]   (no seg ids = every window not yet rendered)
# Adapted from prototypes/bl-ep58/render_v3.sh (task-2db3174c). One window at a time, one fresh render process each,
# under the box-wide render lock (CEO 2026-10-02):
#   - flock -w 7200 /opt/MoonieXHQ/Work/.bl-render.lock around every render, stdin from /dev/null
#   - available RAM >= 3000 MB before each window (waits up to 40 min), stops under 1500
#   - a window that dies with "Sequential screenshot capture stalled" is retried ONCE (after a 60 s breather)
# Arm B = tools/bl_compose.py -> cut/v1 ; arm A = armA/render_window.py (plate + stamp wrapper) -> armA/v1.
# Windows come from prototypes/bl-ep60/segments.json (the seams sit on beat t0s). A finished part is never re-rendered.
ARM=$1; shift
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
WORK=/opt/MoonieXHQ/Work/bl-ep60
case "$ARM" in
  B) C=$WORK/cut/v1;  BEATS=prototypes/bl-ep60/beats.json;       CMD="python3 tools/bl_compose.py" ;;
  A) C=$WORK/armA/v1; BEATS=prototypes/bl-ep60/armA/beats.json;  CMD="python3 prototypes/bl-ep60/armA/render_window.py" ;;
  *) echo "usage: $0 A|B [segNN ...]"; exit 1 ;;
esac
export PATH=/opt/node-v22/bin:$PATH
mkdir -p "$C/parts" "$C/build"
cd "$ROOT" || exit 1
python3 - "$@" > "$C/order.txt" <<'P'
import json, sys
args = sys.argv[1:]
adhoc = [a for a in args if "=" in a]
want = {a for a in args if "=" not in a}
for s in json.load(open("prototypes/bl-ep60/segments.json"))["segments"]:
    if (not want and not adhoc) or s["id"] in want:
        print(s["id"], s["t0"], s["t1"])
for a in adhoc:
    name, _, span = a.partition("=")
    t0, _, t1 = span.partition(":")
    print(name, float(t0), float(t1))
P
render_one() {   # id a b -> rc
  local id=$1 a=$2 b=$3
  flock -w 7200 /opt/MoonieXHQ/Work/.bl-render.lock $CMD --beats "$BEATS" \
    --generator-dir "$WORK/generator" --t0 "$a" --t-max "$b" \
    --out-dir "$C/build/$id" --out "$C/parts/$id.mp4" > "$C/build-$id.log" 2>&1 < /dev/null
}
while read -r id a b <&3; do
  [ -f "$C/parts/$id.mp4" ] && { echo "skip $id (part exists)"; continue; }
  for i in $(seq 1 80); do
    av=$(free -m | awk '/^Mem:/{print $7}')
    [ "$av" -lt 1500 ] && { echo "STOP $id available=$av"; exit 2; }
    [ "$av" -ge 3000 ] && break
    echo "$(date -u +%T) wait $id available=$av"; sleep 30
  done
  [ "$av" -ge 3000 ] || { echo "STOP $id available=$av after waiting 40 min"; exit 2; }
  echo "$(date -u +%T) start $ARM $id $a $b available=$av"
  render_one "$id" "$a" "$b"
  rc=$?
  if [ $rc -ne 0 ] && grep -q "Sequential screenshot capture stalled" "$C/build-$id.log"; then
    echo "$(date -u +%T) $id stalled (rc=$rc), retrying once"; cp "$C/build-$id.log" "$C/build-$id.stalled.log"
    sleep 60; render_one "$id" "$a" "$b"; rc=$?
  fi
  echo "$(date -u +%T) done $ARM $id rc=$rc"
  [ $rc -ne 0 ] && { echo "FAILED $id (see $C/build-$id.log)"; exit 1; }
  rm -f "$C/build/$id/rendered.mp4"
done 3< "$C/order.txt"
echo ALLDONE
