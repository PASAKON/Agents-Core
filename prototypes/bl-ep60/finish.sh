#!/bin/bash
# usage: finish.sh A|B   merge the parts (bl_merge gates), two-pass loudnorm, mux, bl_checker. Run after render_v1.sh ALLDONE.
# bl_merge reads the audio's container duration; audio-hq.mp3 says 90.279 s (25 ms start offset + padding) but decodes to 90.229 s,
# so the merge gets a PCM copy of the same audio (audio-hq-decoded.wav, made once with ffmpeg -c:a pcm_s16le).
ARM=$1
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
W=/opt/MoonieXHQ/Work/bl-ep60
export PATH=/opt/node-v22/bin:$PATH
case "$ARM" in
  B) C=$W/cut/v1;  BEATS=prototypes/bl-ep60/beats.json;      NAME=final-ep60-v1.mp4;       CMP="python3 tools/bl_compose.py" ;;
  A) C=$W/armA/v1; BEATS=prototypes/bl-ep60/armA/beats.json; NAME=final-ep60-armA-v1.mp4;  CMP="python3 prototypes/bl-ep60/armA/render_window.py" ;;
  *) echo "usage: $0 A|B"; exit 1 ;;
esac
cd "$ROOT" || exit 1
[ -f "$W/audio-hq-decoded.wav" ] || ffmpeg -v error -y -i "$W/audio-hq.mp3" -c:a pcm_s16le -ar 44100 "$W/audio-hq-decoded.wav" < /dev/null
$CMP --beats $BEATS --generator-dir $W/generator --t-max 90.2 --out-dir $C/comp-full --no-render > /dev/null 2>&1
python3 tools/bl_merge.py prototypes/bl-ep60/segments.json --parts $C/parts --audio $W/audio-hq-decoded.wav -o $C/merged-$ARM.mp4 \
  --beats $BEATS --compositions $C/comp-full > $C/merge-$ARM.log 2>&1 || { echo "MERGE FAILED"; tail -3 $C/merge-$ARM.log; exit 1; }
tail -1 $C/merge-$ARM.log
M=$(ffmpeg -hide_banner -i $W/audio-hq-decoded.wav -af loudnorm=I=-15.0:TP=-1.0:LRA=11:print_format=json -f null - 2>&1 < /dev/null | sed -n '/^{/,/^}/p')
g() { echo "$M" | grep "\"$1\"" | sed 's/.*: "\(.*\)".*/\1/'; }
ffmpeg -v error -y -i $W/audio-hq-decoded.wav -af "loudnorm=I=-15.0:TP=-1.0:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" -ar 44100 $C/audio-norm.wav < /dev/null
ffmpeg -v error -y -i $C/merged-$ARM.concat.mp4 -i $C/audio-norm.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart $C/$NAME < /dev/null
python3 tools/bl_checker.py --video $C/$NAME --beats $BEATS --take-table prototypes/bl-ep60/take_table.json --composition $C/comp-full/index.html --out $C/checker-$ARM.json > $C/checker-$ARM.log 2>&1
echo "checker rc=$?"
ffmpeg -hide_banner -i $C/$NAME -af loudnorm=I=-15.0:TP=-1.0:print_format=json -f null - 2>&1 < /dev/null | grep -E "input_i|input_tp"
ffprobe -v error -count_frames -show_entries stream=codec_type,duration,nb_read_frames -of csv=p=0 $C/$NAME
