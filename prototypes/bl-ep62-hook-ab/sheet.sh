#!/bin/bash
# usage: sheet.sh <mp4> <out.jpg> <label>  — 16 frames evenly over 0..15 s (t = 0.47 + i*0.9375), 270x480 each, 8x2, time stamped
IN=$1; OUT=$2; LAB=$3; D=$(mktemp -d)
for i in $(seq 0 15); do t=$(awk -v i=$i 'BEGIN{printf "%.2f", 0.47+i*0.9375}')
  ffmpeg -v error -ss $t -i "$IN" -frames:v 1 -vf "scale=270:480,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='$LAB $(printf %02d $((i+1))) ${t}s':x=6:y=6:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6" -y $D/f$(printf %02d $i).png; done
ffmpeg -v error -pattern_type glob -i "$D/f*.png" -vf tile=8x2 -frames:v 1 -q:v 3 -y "$OUT"; rm -rf $D
