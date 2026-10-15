#!/bin/bash
F=/opt/MoonieXHQ/Work/bl-ep62/free10; ID=$1; : > $F/$ID/out/parts.txt
for r in 0-74 75-149 150-224 225-299; do
  [ -s $F/$ID/out/raw-$r.mp4 ] || $F/render10.sh $ID $r > $F/$ID/out/run-$r.txt 2>&1 || { echo "$ID $r FAILED"; grep -m3 -iE "error" $F/$ID/out/render-$r.log | cut -c1-250; exit 1; }
  echo "file 'raw-$r.mp4'" >> $F/$ID/out/parts.txt; done
ffmpeg -v error -f concat -safe 0 -i $F/$ID/out/parts.txt -an -c copy -y $F/$ID/out/raw.mp4
ffmpeg -v error -i $F/$ID/out/raw.mp4 -i $F/pool/voice-10s.wav -map 0:v:0 -map 1:a:0 -frames:v 300 -c:v libx264 -crf 16 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k -t 10 -y $F/$ID/clip-$ID.mp4
echo "$ID final $(ffprobe -v error -select_streams v -show_entries stream=nb_frames,duration -of csv=p=0 $F/$ID/clip-$ID.mp4) $(md5sum < $F/$ID/clip-$ID.mp4 | cut -c1-32)"
