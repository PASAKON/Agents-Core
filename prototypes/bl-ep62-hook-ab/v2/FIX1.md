# Fix 1: PATTERN-1 card (11.67..13.97 s) is too small to read

Edit files only; run no commands. Change ONLY the PATTERN-1 beat; leave every other beat exactly as it is.

The still `cxm-post-account.png` (1080x1920) is mostly black padding: the Facebook post itself is the band
x 0..1080, y 763..1156 (1080 x 393 px). Scaling the whole still to 62% made the post tiny.

New PATTERN-1 card:
- Show ONLY that band (crop: e.g. a wrapper div 860 x 313 with overflow:hidden, the image inside scaled by 860/1080 = 0.7963
  and shifted up by 763 * 0.7963 = 607.6 px; or object-position / background-position — any exact crop).
- Card box: left 110 px, top 600 px, width 860 px, height 313 px, border-radius 24 px, soft shadow, 2 px white/20% border.
- Same entrance as now (slide up 80 px + fade in over 0.35 s from 11.67 s).
- The B-roll behind it (`broll-29.mp4`, finger tapping a red lock): brightness about 60% instead of 45%, so the lock reads.
- Caption and small headline unchanged.

Append one line to NOTES.md saying what you changed.
