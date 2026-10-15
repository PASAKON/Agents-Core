#!/bin/bash
# 6 rows (R0 H0 R1 H1 R2 H2) x 10 frames (0.5 .. 9.5 s), label column on the left
F=/opt/MoonieXHQ/Work/bl-ep62/free10; T=$F/sheet-tmp; mkdir -p $T; FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
declare -A L=([R0]="R0 Remotion / no skill" [H0]="H0 HyperFrames / no skill" [R1]="R1 Remotion / our BL skills" [H1]="H1 HyperFrames / our BL skills+template" [R2]="R2 Remotion / remotion-dev skills" [H2]="H2 HyperFrames / HeyGen skills")
rows=()
for ID in R0 H0 R1 H1 R2 H2; do
  if [ -f $F/$ID/clip-$ID.mp4 ]; then
    ffmpeg -v error -ss 0.5 -i $F/$ID/clip-$ID.mp4 -vf "fps=1,scale=216:384,tile=10x1" -frames:v 1 -y $T/$ID-strip.png
  else ffmpeg -v error -f lavfi -i color=c=gray:s=2160x384 -frames:v 1 -y $T/$ID-strip.png; fi
  ffmpeg -v error -f lavfi -i color=c=black:s=260x384 -vf "drawtext=fontfile=$FONT:text='${ID}':fontcolor=white:fontsize=64:x=20:y=120,drawtext=fontfile=$FONT:text='$(echo ${L[$ID]} | cut -d' ' -f2-)':fontcolor=0xFFD60A:fontsize=17:x=20:y=210" -frames:v 1 -y $T/$ID-label.png
  ffmpeg -v error -i $T/$ID-label.png -i $T/$ID-strip.png -filter_complex hstack -y $T/$ID-row.png; rows+=(-i $T/$ID-row.png)
done
ffmpeg -v error "${rows[@]}" -filter_complex "vstack=inputs=6" -q:v 3 -y $F/sheet-free10-6rows.jpg && echo sheet ok
