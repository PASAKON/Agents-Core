#!/usr/bin/env bash
# shot-motion.sh — does a "busy" shot actually REARRANGE, or is it a tableau
# with moving hands? Compares the people-band of an early frame against later
# ones and prints the percentage of that band that changed.
#
#   bash scripts/shot-motion.sh <clip.mp4> [t0] [t1 t2 t3 ...]
#
# Measured on «Sorry, Sir» 2026-09-11:
#   S2AC take 1 (failed)  10%   |  flat across 7s/12s/15.5s
#   S2AC take 2 (failed)  11%   |  flat across 7s/12s/15.5s  <- same sheet, same number
#   A genuinely rearranging group should be well clear of that.
#
# A LOCKED camera is assumed. With a moving camera the background changes too
# and the number inflates (S2PT take 4, tracking shot: 47% whole-frame) — the
# reading is only meaningful shot-to-shot on a locked frame.
set -euo pipefail
CLIP="${1:?usage: shot-motion.sh <clip.mp4> [t0] [t1 ...]}"
T0="${2:-1}"; shift 2 2>/dev/null || shift 1 2>/dev/null || true
TIMES=("$@"); [ ${#TIMES[@]} -eq 0 ] && TIMES=(7 12 15.5)
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# middle horizontal band = where a standing cast lives; ignores ceiling and floor
CROP="crop=iw:ih/2:0:ih/4,scale=160:45,format=gray"
ffmpeg -loglevel error -ss "$T0" -i "$CLIP" -frames:v 1 -vf "$CROP" -f rawvideo "$TMP/a.raw" -y

echo "$(basename "$CLIP") — people-band change vs t=${T0}s"
for t in "${TIMES[@]}"; do
  ffmpeg -loglevel error -ss "$t" -i "$CLIP" -frames:v 1 -vf "$CROP" -f rawvideo "$TMP/b.raw" -y 2>/dev/null || continue
  python3 - "$TMP/a.raw" "$TMP/b.raw" "$t" <<'PY'
import sys
a=open(sys.argv[1],'rb').read(); b=open(sys.argv[2],'rb').read()
if not a or not b or len(a)!=len(b):
    print(f"  t={sys.argv[3]:>6}s   (no frame)"); raise SystemExit
d=[abs(x-y) for x,y in zip(a,b)]
pct=sum(1 for v in d if v>20)*100//len(d)
flag="TABLEAU — the group never rearranged" if pct<15 else ""
print(f"  t={sys.argv[3]:>6}s   changed {pct:3d}%   {flag}")
PY
done
echo
echo "Reading it — the TREND matters more than the level:"
echo "  rising (44 -> 46 -> 54)  a real scene drifts further from its opening as it runs"
echo "  flat   (11 ->  9 -> 11)  a tableau stays the same distance from its opening forever"
echo "A flat low number means gestures moved and people did not."
echo "See CTO_Seedance2.5_Higgsfield SKILL.md, 'Measuring motion on a Seedance take'."
