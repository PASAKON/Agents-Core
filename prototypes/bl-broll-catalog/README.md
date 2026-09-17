# BL B-roll catalogue — working state (not yet in Drive)

65 clips in `~/Desktop/archive` (Seedance 2.0, Higgsfield Unlimited, 3–7 Aug 2026,
all 1080x1920 @24fps, 8.08 s). Named by AI from the 4-frame sheets; 11 flagged
for CEO review (`REVIEW-flagged.jpg`, `review` field in the JSON).

- `broll-catalog.json` — one row per clip: proposed filename, Thai + English tags,
  subject / motion / mood, `fit` (visual: BL / BORDER / GEN), `avatar`,
  measured palette (`dark_pct`, `red_pct`, `blue_pct`, `palette_fit`), `review`.
- `CATALOG.md` — the same, one grep-able line per clip. This is what a worker reads.
- `sheets/<hf-id>.jpg` — 4 frames (0.3 / 2.7 / 5.4 / 7.8 s), ~40 KB each. A worker
  opens ONE of these to confirm a pick; it never opens the video.
- `index/index-N.jpg` — 10 clips per image, the naming pass input.

Filename rule (gdrive-filing, AI Assets): `(purpose) (D-M-YYYY) (Seedance 2.0).mp4`,
purpose in English kebab so Drive search and shells are safe; Thai lives in tags.

`fit` is the visual call and is authoritative. `palette_fit` is a crude first
filter (dark ≥ 55 % and not blue) and it mislabels every avatar clip and every
bright-object-on-dark clip as GEN — 13 of 27 disagreements are that. By eye:
BL 47 · BORDER 7 · GEN 11 → 83 % usable for the channel, which matches the
CEO's "80 %"; the tool's 57 % was its own bias.

Destination (CEO 2026-09-18): Drive `AI Assets` = `14uc0nxq0ZmaS0GZuCq7hZOl1ROeUYRbV`
(this id is missing from the gdrive-filing table — add it when uploading),
channel folder `BLACK LIQUIDITY (9:16)` = `1vg8j7DY_hPE-X3yyTsp6ZrM8Gf72cfVG`.
Upload has NOT happened; it waits for the CEO's answers on the 11 flags.
