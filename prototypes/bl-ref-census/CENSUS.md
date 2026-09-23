# CENSUS — BLACK LIQUIDITY reference edit (task-82380776)

Source: `@black_liquidity/video/7612158317695159573`, 85.240454s, 1080x1920, 30fps, 4,452,286 bytes.
Full data: `census.json`. Answer key: `groundtruth.tsv` (45 spoken lines). Visual check: `timeline.html`.

## Counts per phase

| Phase | Count | Notes |
|---|---|---|
| P1 shots | 16 | Every one of the 85.24s accounted for, contiguous, no gaps (verified programmatically). |
| P2 focus events | 14 | 2 SKILL-verified (hook slide, avatar shrink@51.27), 2 independently re-measured to SKILL's own numbers (spotlight@4.40, yellow-onsets), rest newly found this pass. |
| P3 text blocks | 14 | Covers every *distinct* channel-added text element; the ~85 individual per-utterance bottom-caption swaps are represented by their pattern + 9 named examples, not itemized one-by-one (see "Could not measure"). |
| P4 SFX onsets | 15 | Plus 2 confirmed silences-where-a-sound-was-expected. |
| P5 watermark | 1 | Constant for the full 85.24s. |

**P1 entry-type breakdown:** 9 hard cuts, 4 dissolves (all estimated, no clean diff signature — that is what makes them dissolves), 1 animated shrink (SKILL-verified), 1 flash-wipe. Matches the reference's own editing grammar closely — SKILL's existing note "cuts hard only about every 6s" holds (9 hard cuts / 85s ≈ one every 9.5s, in the same order of magnitude once the 4 soft dissolves and the one shrink are counted separately from "hard cuts").

## Event density per 5s window (P1 shot starts + P2 + P3 + P4 combined)

```
 0- 5s: 8    15-20s: 4    30-35s: 2    45-50s: 3    60-65s: 1    75-80s: 2
 5-10s: 5    20-25s: 4    35-40s: 0    50-55s: 3    65-70s: 3    80-85s: 3
10-15s: 3    25-30s: 2    40-45s: 2    55-60s: 6    70-75s: 7
```

Two dead zones stand out: **35-40s** (0 events) and **60-65s** (1 event) — both fall
inside a single sustained full-frame verdict/explainer shot with no plate or
graphic changes, i.e. genuinely quiet stretches, not a measurement gap. The
busiest windows are **0-5s** (hook: slide + logo pop + cut + SFX) and **70-75s**
(the CTA/profile-card/flash/logo-card cluster — four distinct plate changes in
5 seconds, the densest stretch in the whole edit).

## Patterns, with numbers

- **Full-frame vs composite:** 6 full-frame shots totalling ~32.8s (38.5%),
  10 composite/app-UI/logo-card shots totalling ~52.4s (61.5%). Full-frame is
  reserved for hook, verdict and CTA-framing lines; composite is reserved for
  every line that names something show-able (a number, a table row, a
  balance) — matches SKILL's existing "show vs verdict" framing exactly.
- **Cuts cluster at section boundaries, not randomly.** All 9 hard cuts land
  within 0.15s of a spoken-line boundary (see `groundtruth.tsv`'s `entry_type`
  column) — none happen mid-sentence.
- **The two "text pop that isn't a cut" traps.** 14.033s (strikethrough +
  new-line reveal) and the 71.6/71.8s cluster (a pulsing Follow button) both
  produce frame-diff spikes the same size as a real hard cut (0.2-0.6) with
  no plate or avatar-mode change underneath. A checker built on frame-diff
  alone will over-count cuts by ~2 unless it also checks plate identity.
- **Yellow-highlight-to-spoken-word sync is tight and consistent where it's a
  true highlighter sweep:** 3 of 3 checked land within 0.02-0.15s of the
  target word (SPREAD 9.067→9.220 word start, REBATE 34.400→34.400 word start
  — exact, Exness 57.167→57.180 word start). The 2 lower-confidence yellow
  onsets (69.6, 76.2) are app-UI icon pops, not highlighter sweeps, and sync
  much more loosely (0.26-0.4s) — worth treating as a different P2 event type
  in the checker, not the same "highlighter_sweep" bucket.
- **SFX favor cuts and highlights over ordinary speech.** Of 15 onsets found,
  10 land within 0.2s of a P1 cut/transition or a P2 highlight/pop; only a
  handful are weak/ambiguous. Two notable silences: the 9.07 SPREAD highlight
  and the 64.533 hard cut (SKILL's sharpest, "0 in-between frames") both carry
  **no** SFX at all, despite similar events elsewhere always having one —
  recorded as real silences per the task brief, not as gaps in measurement.

## TRACKER-DRIFT FINDING (important — corrects an existing SKILL claim)

`seed/track.py`, re-run over the full 85.24s (`measurements/track_full.txt`),
loses head-lock twice **inside shot 3 (5.233-20.267s)**: scale falsely drops
to 0.66-0.70 (composite-level) during **9.5-14.0s** and **19.3-20.267s**, while
every other full-frame shot in the file holds a tight 0.98-1.14 scale range
throughout (checked shot-by-shot, see RUNLOG.md 22:1x entries). Ten
independent 0.2-0.5s-step contact-sheet passes across this shot all show the
avatar full-frame, centered, static — it never moves or shrinks here. This
is the exact drift failure mode the seed's own README already warned about
(the first template version "swallowed the static hook text, so it tracked
the text, not the head") — it resurfaces here because the kinetic header
block (`ค่า SPREAD สูงเพราะ?` + checkbox lines) sits close enough to the
head's search window to occasionally out-score it.

This also means **SKILL §6d's existing table is incomplete, not wrong for
what it covers**: its "9s, 19s" shrink-into-composite entries describe this
same drift, not real avatar switches — there is no plate change and no
avatar-mode change at either timestamp in the actual video (confirmed by
eye, by frame-diff, and by the plate content itself: 5.233-20.267s is one
continuous full-frame shot). The CTO's SKILL-fold should mark those two
table rows `[SUPERSEDED]` against this task's evidence (RUNLOG.md, this
file, `measurements/track_full.txt`) — not delete them, since the underlying
easing numbers for the *real* switches (46.233, 51.27-52.17, 59.5, 64.533,
71.1, 80.333) are unaffected and several are now independently re-confirmed.

## Could NOT measure, and why

- **Per-utterance bottom-caption boxes/styles, individually.** ~85 short
  captions swap across the file (one per spoken line, per the reference's
  own caption style); pixel-perfect box/entrance/exit for every single one
  would need a full-res read per caption. Recorded the pattern once plus 9
  representative examples in `census.json`'s `p3_text_blocks` instead.
- **Music-bed presence/level is inconclusive**, not absent — see
  `census.json.p4_music_bed`. Band-energy comparison (low/mid/high dB across
  speech vs. gaps) found no clearly separate bed; a proper vocal-isolation
  pass (torch was available per the brief but not used, given time budget)
  would be needed to rule it in or out with confidence.
- **P2 pan/zoom/scroll "eased by eye" entries** (XM-page pan 2.0-4.4s, app
  scroll 72.3-80.333s) are not independently fit to an easing curve — no
  stable anchor point to track (the content itself moves, not a fixed
  template like the head), unlike the avatar moves and the spotlight/yellow
  events which all have hard measurements behind them.
- **Exact pixel boxes for P3 text blocks** are estimates read by eye off
  contact sheets, not measured against the frame edges/avatar box the way
  the task asks ("distance in px... that number is what ไม่บังจุด Focus
  และไม่ติดขอบ means as a number") — flagged per-row in `census.json` as
  `dist_to_*_px: "estimate"`. A proper pass would need full-res crops of
  every text block plus a consistent bbox-detection method; not built this
  round given the P1-completeness priority.
- **The MoonieX logo-card's exact in/out frame** (shot 14, 72.05-72.3s) —
  two single-frame full-res grabs both missed its ~0.2s window; timing is
  bounded from a 0.1s-step contact sheet instead, not frame-exact.

## Compliance note (not a fix — the reference is not being cut)

Shot 13 (71.1-72.05s) shows the channel's own public TikTok profile carrying
an explicit rebate-link CTA in the bio ("คืน Rebate 90%...ติดต่อไลน์
@mooniex...https://www.openlink.co/mooniex"), read verbatim off a full-res
frame. Per `blackliquidity-cut` SKILL §6b, this class of link belongs in
closed channels only, not a public post. Flagging per the task brief's
instruction ("If the script you were handed does that, say so in your report
rather than cutting around it") — nothing here was cut or altered, this is
the human editor's own ฿1300 reference, included for completeness.
