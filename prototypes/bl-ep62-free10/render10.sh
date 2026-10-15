#!/bin/bash
# usage: render10.sh <ID> [frames]  — R*: remotion (optional --frames range → out/raw-<range>.mp4), H*: hyperframes; logs wall time
set -e; ID=$1; RANGE=$2; F=/opt/MoonieXHQ/Work/bl-ep62/free10; export PATH=/opt/node-v22/bin:$PATH
mkdir -p $F/$ID/out; cd $F/$ID; free -m | awk 'NR==2{print "avail MB", $7}'
case $ID in
  R*) OUT=out/raw${RANGE:+-$RANGE}.mp4; CMD="npx remotion render src/index.ts Clip $OUT --codec h264 --concurrency 1 --timeout 120000 --offthreadvideo-cache-size-in-bytes=209715200 --offthreadvideo-threads=1 ${RANGE:+--frames=$RANGE}";;
  H*) OUT=out/raw.mp4; CMD="npx --yes hyperframes@0.8.40 render -o $OUT --low-memory-mode --workers 1 --protocol-timeout 600000";;
esac
S=$(date +%s); flock -w 3600 /opt/MoonieXHQ/Work/.bl-render.lock bash -c "$CMD" < /dev/null > out/render${RANGE:+-$RANGE}.log 2>&1 || { tail -20 out/render${RANGE:+-$RANGE}.log; exit 1; }
echo "$ID ${RANGE:-all} render $(( $(date +%s)-S )) s" | tee -a $F/render-times.txt
