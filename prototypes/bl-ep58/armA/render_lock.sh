#!/bin/bash
# usage: render_lock.sh [rev] -- claims windows with mkdir locks so two drivers share the list (EP58 arm A)
W=/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__video_editor__task-4305b93b
C=/opt/MoonieXHQ/Work/bl-ep58/armA
export PATH=/opt/node-v22/bin:$PATH
cd "$W" || exit 1
python3 - "$1" > $C/order-${1:-fwd}.txt <<'P'
import json,sys
s=json.load(open('/opt/MoonieXHQ/Work/bl-ep58/armA/segments.json'))['segments']
if len(sys.argv)>1 and sys.argv[1]=='rev': s=s[::-1]
for x in s: print(x['id'],x['t0'],x['t1'])
P
while read id a b <&3; do
  [ -f "$C/parts/$id.mp4" ] && continue
  mkdir "$C/lock-$id" 2>/dev/null || continue
  echo "$(date -u +%T) start $id $a $b"
  python3 prototypes/bl-ep58/armA/render_window.py --beats prototypes/bl-ep58/armA/beats.json \
    --generator-dir /opt/MoonieXHQ/Work/bl-ep58/generator --t0 "$a" --t-max "$b" \
    --out-dir "$C/build/$id" --out "$C/parts/$id.mp4" > "$C/build-$id.log" 2>&1 < /dev/null
  rc=$?
  echo "$(date -u +%T) done $id rc=$rc"
  [ $rc -ne 0 ] && { echo FAILED $id; exit 1; }
  rm -f "$C/build/$id/rendered.mp4"
done 3< $C/order-${1:-fwd}.txt
echo ALLDONE-${1:-fwd}
