#!/bin/bash
# Put a music bed quietly under a finished cut, ducked by the dialogue (CEO 2026-10-01: Mimi episodes carry the M1 piano bed).
# usage: tools/film_music_mix.sh <cut.mp4> <music.wav|mp3> <out.mp4> [music_dB=-4] [start_s=3] [fade_in_s=3] [fade_out_s=5]
# Recipe measured on EP1 (dialogue about -16 dB RMS, track -18.6 LUFS): -4 dB puts the music about 16 dB under speech
# and about -26 dB absolute in the pauses (a gentle swell between lines). Lower number = quieter. Video is copied.
# Traps: alimiter MUST be level=disabled (its default auto-gains the whole mix); never judge the level from (mix - cut)
# after AAC encoding (see CMO_Gate_Flow_Omni1.1_FilmQC field note 2026-10-01).
set -euo pipefail
cut="$1"; music="$2"; out="$3"; vol="${4:--4}"; start="${5:-3}"; fin="${6:-3}"; fout="${7:-5}"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$cut")
mdur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$music")
fo_at=$(python3 -c "print(max(0,min($mdur,$dur-$start)-$fout))")
ms=$(python3 -c "print(int($start*1000))")
G="[1:a]aformat=channel_layouts=mono,volume=${vol}dB,afade=t=in:d=${fin},afade=t=out:st=${fo_at}:d=${fout},adelay=${ms},apad=whole_dur=${dur}[m];[0:a]asplit=2[d][sc];[m][sc]sidechaincompress=threshold=0.05:ratio=2.5:attack=40:release=700:makeup=1[md];[d][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.97:level=disabled[a]"
ffmpeg -y -v error -i "$cut" -i "$music" -filter_complex "$G" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 128k "$out"
echo "mixed -> $out ($(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out") s; music ${vol} dB from ${start}s)"
