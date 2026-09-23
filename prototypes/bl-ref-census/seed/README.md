# Seed for the reference census (CTO 3d312dd6, 2026-09-23)

Measurement scripts from the CTO's first pass over the ฿1300 reference edit
(TikTok @black_liquidity/video/7612158317695159573, 85.24 s, 1080x1920, 30 fps).
The results are folded into `.claude/skills/blackliquidity-cut/SKILL.md` §6d.

- `track.py`: head tracker. Multi-scale NCC in plain numpy (no cv2/scipy on the Mac).
  Usage: `python track.py ref.mp4 '[[t0,t1],...]'` prints one line per frame:
  `t scale cx cy top ncc`. The template is beanie + sunglasses from frame 0
  (y 160-260, x 81-189 on a 270x480 grid). **Trap:** the first template started at y95
  and swallowed the static hook text, so it tracked the text, not the head. Always
  check a tracker against one known value before a full run.
- `fit.py`: reads track output, finds the motion segment, and fits GSAP easings by RMSE.
- `transcript-small.txt`: faster-whisper `small` segments (Thai, rough). The word-level
  pass is character-split for Thai; join the pieces without spaces before matching keywords.

Already measured (verify, do not re-derive): entry to composite = sine.out shrink over
0.7-0.9 s after the plate swaps; exits = hard cut; the hook slide 0.23-1.43 s is power1.out
+298 px; yellow onsets 9.07 / 34.47 / 57.20 against spoken 9.22 / 34.40 / 57.18; the spotlight
circle at 4.40-5.15 s.
