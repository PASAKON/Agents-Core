#!/bin/bash
# One window at a time, under the box-wide render lock; stops if available RAM < 1500 MB, waits if < 3000 (CEO rules 2026-10-02).
W=/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__video_editor__task-3cf9c2f8
C=/opt/MoonieXHQ/Work/bl-ep58/armA
export PATH=/opt/node-v22/bin:$PATH
cd "$W" || exit 1
python3 -c "
import json
for x in json.load(open('$C/segments.json'))['segments']: print(x['id'],x['t0'],x['t1'])" > $C/order-seq.txt
while read id a b <&3; do
  [ -f "$C/parts/$id.mp4" ] && continue
  for i in 1 2 3 4 5 6; do
    av=$(free -m | awk '/^Mem:/{print $7}')
    [ "$av" -lt 1500 ] && { echo "STOP $id available=$av"; exit 2; }
    [ "$av" -ge 3000 ] && break
    echo "$(date -u +%T) wait $id available=$av"; sleep 30
  done
  [ "$av" -ge 3000 ] || { echo "STOP $id available=$av after waiting"; exit 2; }
  echo "$(date -u +%T) start $id $a $b available=$av"
  flock -w 7200 /opt/MoonieXHQ/Work/.bl-render.lock python3 prototypes/bl-ep58/armA/render_window.py \
    --beats prototypes/bl-ep58/armA/beats.json --generator-dir /opt/MoonieXHQ/Work/bl-ep58/generator \
    --t0 "$a" --t-max "$b" --out-dir "$C/build/$id" --out "$C/parts/$id.mp4" > "$C/build-$id.log" 2>&1 < /dev/null
  rc=$?
  echo "$(date -u +%T) done $id rc=$rc"
  [ $rc -ne 0 ] && { echo FAILED $id; exit 1; }
  rm -f "$C/build/$id/rendered.mp4"
done 3< $C/order-seq.txt
echo ALLDONE
