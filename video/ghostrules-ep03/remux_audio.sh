#!/bin/bash
# Swap the ambience bed with no re-render.  usage: remux_audio.sh NEWBED.wav VIDEO.mp4 OUT.mp4 [bed_gain_db]
# NEWBED: any ambience loop; it must already cover 801 s (loop it first, >=1.5 s crossfades) and be mono/stereo.
# The bed stem ep03_bed.wav carries the calm (jump scare) and rain-crossfade envelopes; the new bed should carry the same dips,
# so apply the same envelope: envelope = ep03_bed.wav's own shape. Simplest: replace by building with build_mix.py NEWBED OUTDIR.
set -e
D=/opt/MoonieXHQ/Work/task-f143f9cf/out
ffmpeg -y -i "$2" -i $D/ep03_nobed.wav -i "$1" -filter_complex "[1][2]amix=inputs=2:normalize=0:duration=longest,pan=stereo|c0=c0|c1=c0,alimiter=limit=0.8414:attack=5:release=60:level=0[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest "$3"
