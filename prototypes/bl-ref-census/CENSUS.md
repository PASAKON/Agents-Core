# CENSUS — BLACK LIQUIDITY reference edit (task-82380776)

Source: `@black_liquidity/video/7612158317695159573`, 85.240454s, 1080x1920, 30fps, 4,452,286 bytes.
Full data: `census.json`. Answer key: `groundtruth.tsv` (45 spoken lines). Visual check: `timeline.html`.

## CORRECTION NOTICE (2026-09-23, CTO review)

The first submission's P1 was wrong: it merged 4 real shots (5.233-20.267s)
into one, on the strength of a "tracker drift" claim that was itself wrong —
the avatar really does shrink into composite twice there (9.33-10.23s and
19.13-19.83s), exactly as SKILL §6d already said, and I dismissed that
because I misread my own coarse 0.5s-step contact sheets rather than trusting
the tracker or re-checking at real frame density. The CTO caught it by
reading `reference/avatar-shrink-motion.jpg` directly. Re-verifying that
fix at 15fps then surfaced three more errors this file corrects:

1. **Shots 20.267-24.600 and 24.600-27.2ish had their plate identities
   swapped** (the rebate table and the EURUSD chart were labeled backwards).
2. **A fabricated shot boundary at ~27.2s** (a dissolve that doesn't exist —
   full re-scan of `frame_diff.csv` found zero signal there; 24.600-46.233 is
   one continuous shot).
3. **Two "soft dissolve, estimate" boundaries (~57.2s, ~68.8s) were both off
   by 0.5-0.6s** and were actually real hard cuts (56.633s, 68.267s) — my
   absolute frame-diff threshold (0.12) filtered them out because both cuts
   land between two similarly-bright plates (white-on-white, navy-on-navy),
   which produces a much smaller pixel delta than a cut between a dark and a
   light scene even though the plate change is just as real. A
   relative-baseline rescan (diff minus local moving average) caught both.

Also fixed per CTO note: shot 1's plate re-classified `chart b-roll` (was
wrongly `red studio`), and the MoonieX logo-card's notes no longer claim "no
connection to us" — it is the org's own brand; that line is retracted.

**P1 shot count: 16 → 18.** Every number below is recomputed from the fixed
`census.json`, not hand-carried from the rejected version.

## Counts per phase

| Phase | Count | Notes |
|---|---|---|
| P1 shots | 18 | Every one of the 85.24s accounted for, contiguous, no gaps (verified programmatically). |
| P2 focus events | 18 | Includes 2 avatar_shrinks + 2 plate_dissolves this file previously missed entirely (see correction notice). |
| P3 text blocks | 14 | Covers every *distinct* channel-added text element; the ~85 individual per-utterance bottom-caption swaps are represented by their pattern + 9 named examples, not itemized one-by-one (see "Could not measure"). |
| P4 SFX onsets | 20 | Plus 2 confirmed silences-where-a-sound-was-expected. |
| P5 watermark | 1 | Constant for the full 85.24s. |

**P1 entry-type breakdown:** 12 hard cuts, 1 dissolve, 2 combined dissolve+shrink switches (SKILL-verified), 1 animated shrink (SKILL-verified), 1 flash-wipe, 1 cold open. The two dissolve+shrink switches are the ones this file previously lost entirely — a plate dissolves in behind the still-full avatar (~0.2s), then the avatar shrinks into composite over the following ~0.9s (sine.out both times, SKILL-verified RMSE 0.032-0.067).

## Event density per 5s window (P1 shot starts + P2 + P3 + P4 combined)

```
 0- 5s: 8    15-20s: 7    30-35s: 2    45-50s: 3    60-65s: 1    75-80s: 2
 5-10s:10    20-25s: 4    35-40s: 0    50-55s: 3    65-70s: 4    80-85s: 3
10-15s: 5    25-30s: 1    40-45s: 2    55-60s: 7    70-75s: 7
```

The 5-20s range is now visibly the second-busiest stretch in the file (10, 5,
7 per window) once the two real avatar-shrink switches and their plate
dissolves are counted — it was flattened to near-zero density in the
rejected version because that whole range had been wrongly treated as one
static shot. **35-40s** (0 events) is now the only true dead zone, sitting
inside the long 24.600-46.233s EURUSD-chart shot between the REBATE-chip
build (ends ~35) and the next icon pop (~41.5) — a genuinely quiet stretch,
not a measurement gap. The busiest windows are **5-10s** (plate dissolve +
avatar shrink + header text arriving) and **70-75s** (the CTA/profile-card/
flash/logo-card cluster — four distinct plate changes in 5 seconds).

## Patterns, with numbers

- **Full-frame vs composite:** 7 full-frame shots totalling ~26.3s (30.9%),
  11 composite/app-UI/logo-card shots totalling ~58.9s (69.1%). Full-frame is
  reserved for hook, verdict and CTA-framing lines; composite is reserved for
  every line that names something show-able (a number, a table row, a
  balance) — matches SKILL's existing "show vs verdict" framing exactly.
- **Cuts cluster at section boundaries, not randomly.** All 12 hard cuts land
  within 0.15s of a spoken-line boundary (see `groundtruth.tsv`'s `entry_type`
  column) — none happen mid-sentence.
- **A real cut can produce a SMALL frame-diff spike if both plates are
  similarly bright.** 56.633s and 68.267s are both genuine 1-frame hard cuts
  (confirmed by direct frame read) but only score 0.048-0.059 on a full-frame
  diff — an order of magnitude below the ~0.3-0.65 that every other hard cut
  in the file produces — because each cuts between two plates of similar
  overall luminance (white table -> white table; dark navy -> dark navy). A
  checker using one flat diff threshold will miss cuts like these; a
  relative-baseline score (diff minus local moving average) catches them.
- **One remaining "spike that isn't a cut" trap.** The 71.6/71.8s cluster (a
  pulsing Follow button on the profile-card plate) produces a frame-diff
  spike the same size as a real hard cut (0.2-0.4) with no plate or
  avatar-mode change underneath — the only false positive left after fixing
  the errors above (14.033 is now correctly a real cut, not a false one).
- **Yellow-highlight-to-spoken-word sync is tight and consistent where it's a
  true highlighter sweep:** 3 of 3 checked land within 0.02-0.15s of the
  target word (SPREAD 9.067→9.220 word start, REBATE 34.400→34.400 word start
  — exact, Exness 57.167→57.180 word start). The 2 lower-confidence yellow
  onsets (69.6, 76.2) are app-UI icon pops, not highlighter sweeps, and sync
  much more loosely (0.26-0.4s) — worth treating as a different P2 event type
  in the checker, not the same "highlighter_sweep" bucket.
- **SFX favor cuts and highlights over ordinary speech.** Of 20 onsets found,
  most land within 0.2-0.3s of a P1 cut/transition or a P2 highlight/pop/
  shrink; only a handful are weak/ambiguous. Two notable silences: the 9.07
  SPREAD highlight and the 64.533 hard cut (SKILL's sharpest, "0 in-between
  frames") both carry **no** SFX at all, despite similar events elsewhere
  always having one — recorded as real silences per the task brief, not as
  gaps in measurement.

## Could NOT measure, and why

- **Per-utterance bottom-caption boxes/styles, individually.** ~85 short
  captions swap across the file (one per spoken line, per the reference's
  own caption style); pixel-perfect box/entrance/exit for every single one
  would need a full-res read per caption. Recorded the pattern once plus 9
  representative examples in `census.json`'s `p3_text_blocks` instead.
- **The exact strikethrough timing for the wrong-answer checkbox** (shot 4)
  is a re-estimate (~10.5-11.2s), not a re-measurement — a full-res frame at
  t=12.0 proved it happens before 12.0 (the original 14.0 claim was wrong),
  but the true onset was not pinned down frame-by-frame given time spent
  fixing the bigger P1 structural errors first.
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
- **The MoonieX logo-card's exact in/out frame** (shot 16, 72.067-72.3s) —
  two single-frame full-res grabs both missed its ~0.2s window; timing is
  bounded from a 0.1s-step contact sheet instead, not frame-exact.

## Compliance note (not a fix — the reference is not being cut)

Shot 15 (71.1-72.067s) shows the channel's own public TikTok profile carrying
an explicit rebate-link CTA in the bio ("คืน Rebate 90%...ติดต่อไลน์
@mooniex...https://www.openlink.co/mooniex"), read verbatim off a full-res
frame. Per `blackliquidity-cut` SKILL §6b, this class of link belongs in
closed channels only, not a public post. Flagging per the task brief's
instruction ("If the script you were handed does that, say so in your report
rather than cutting around it") — nothing here was cut or altered, this is
the CEO's own old post, included for completeness.
