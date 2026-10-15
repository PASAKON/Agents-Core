#!/bin/bash
# usage: render.sh v1|v2 — one render under the box-wide render lock, then the same narration muxed on, then a sheet
set -e; V=$1; H=/opt/MoonieXHQ/Work/bl-ep62/hook-ab; export PATH=/opt/node-v22/bin:$PATH
mkdir -p $H/$V/out
free -m | awk 'NR==2{print "avail MB", $7}'
cd $H/$V
if [ "$V" = v1 ]; then RAW=$H/v1/out/raw-v1.mp4; CMD="npx --yes hyperframes@0.8.40 render -o $RAW"
else RAW=$H/v2/out/raw-v2.mp4; CMD="npx remotion render src/index.ts Hook $RAW --codec h264 --concurrency 1 --timeout 120000"; fi
flock -w 3600 /opt/MoonieXHQ/Work/.bl-render.lock bash -c "$CMD" < /dev/null
ffmpeg -v error -i $RAW -i $H/assets/audio-0-15.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -t 15 -y $H/$V/hook-$V.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,duration -of csv=p=0 $H/$V/hook-$V.mp4
md5sum $H/$V/hook-$V.mp4
$H/sheet.sh $H/$V/hook-$V.mp4 $H/$V/sheet-$V.jpg $(echo $V | tr a-z A-Z)
echo DONE $V
