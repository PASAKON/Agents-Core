# S2R Fix-1 take 1 — THE BATTLE — 2026-09-07

STATUS: FLAGGED — three fires, three copyright rejections, no clean render.
Stopped at 3 per CTO's fire-3 plan (no fire 4).

## Setup verification (all three fires)

- innerWidth readback: 1280×754 (>=1280 threshold met)
- "Credits are running low!" banner: closed via its own X each time it reappeared
  (fires 1–2 and again before fire 3)
- Six fields verified visually before every fire: 16:9 · 720p · Seedance 2.5 ·
  20s · High · Sound On
- Price zoom: `UNLIMITED · ~~440~~ · 0` confirmed by zoomed screenshot before
  every fire (never trusted the JS scrape — one read showed a decoy
  "GENERATE8045" string that did not match the real zoomed button)
- Paste method: base64 synthetic `ClipboardEvent('paste')` dispatched on the
  focused contenteditable, then End → space → Backspace tap
- Chip gate: 14/14 unique chips lime, 0 unresolved `@`, on every one of the
  three fires (re-verified after the previz detach before fire 3, per
  playbook's "a detach can silently delete an adjacent chip" warning — none
  did)
- Gate greps (paste block only): `nearest|extreme foreground|very front|
  floating|toward the mark|backs to the room` → 0 matches. `prompt-lint.py`
  → exit 0.

## Fire 1 — WITH previz

- Previz: `docs/S2R-Render.MP4` attached via References panel Upload, byte-
  verified against the live CDN URL: `HEAD` content-length `4528874` bytes,
  matching `ls -l docs/S2R-Render.MP4` exactly. readyState 0 on the tile,
  Generate stayed enabled (benign per playbook).
- Fired once. Confirmed by "Generation started" toast + asset count 677→678
  + new Processing card.
- Render finished ~15–20 min later: **Rejected due to copyright
  restrictions.** (read from the card's `title` attribute — the rejection is
  invisible in the composer, exactly as the playbook warns).

## Fire 2 — SAME paste, unchanged, WITH previz (sheet's own retry rule)

The sheet's own notes say: *"ON A REFUSAL OR A COPYRIGHT REJECTION: re-fire
the same thing once, unchanged — these rejections are not deterministic.
Only stop if the same clip is refused twice."* Followed that rule (confirmed
with CTO mid-task). Reload had reset Unlimited/720p/20s — rebuilt all six
fields + re-toggled Unlimited + re-verified 14/14 chips + confirmed same
previz still attached (same CDN URL, same readyState 0) before firing.

- Fired once. Confirmed by toast + asset count 678→679 + new Processing card.
- Render finished ~15–20 min later: **Rejected due to copyright
  restrictions.** — same message, same failure.

## Fire 3 — SAME paste, unchanged, NO previz (CTO's contingency plan)

CTO's working theory: every named Element already cleared S2Q's copyright
gate and the prompt names only Carrington/Valder (both proven elsewhere), so
the suspect was the **previz video's floating on-screen labels**
(REGISTRAR / VALDER / MADAME baked into the grey-block reference clip —
confirmed visible in a zoom of the tile: "REGISTRAR", "BODYGUARD",
"GENTLEMAN", "VALDER", "MADAME"). CTO's plan: if fire 2 is rejected again,
fire 3 immediately with the same paste and the chip gate re-checked, but
**no previz attached**, then stop regardless of outcome.

- Removed the previz reference tile via its hover-X. Re-verified 14/14 chips
  still bound, 0 video refs in the DOM.
- Banner reappeared and fields had reset again (1080p/5s) — rebuilt 720p,
  20s, re-toggled Unlimited, re-confirmed `UNLIMITED · ~~440~~ · 0`.
- Fired once, **without** the previz. Confirmed by toast + asset count
  679→680 + new Processing card.
- Render finished ~15–20 min later: **Rejected due to copyright
  restrictions.** — same message again.

This rules out the previz-label theory: fire 3 had no previz at all and was
rejected identically. The block is coming from something in the text prompt
itself (or Element/reference set), not the previz overlay text.

## Verdict

All three fires: **Rejected due to copyright restrictions.** Zero clean
renders. No NSFW/sensitive-content banner, no credits-refunded banner — this
is specifically the copyright-restriction rejection type, confirmed via each
card's `title` attribute (invisible in the composer UI itself, as flagged by
FIRE-PLAYBOOK.md).

Evidence: `docs/reports/frames-s2r-t1/three-rejections.png` — zoomed
screenshot of all three job cards side by side, each showing the same
eye-off + info icon pattern with the copyright-rejection title.

The paste block was independently checked before firing and contains **zero**
occurrences of "MADAME" or "THIBAULT" or the character's real name — the
name-stripping fix from the S2Q incident was already applied to this sheet
before this task began. The rejection is happening despite that fix already
being in place, on a fully name-stripped prompt, with and without the previz
reference.

## Frame checks

Not performed — no clip rendered clean on any of the three fires. Nothing to
extract frames from.

## Cost

Zero credits spent across all three fires — Unlimited mode confirmed
`~~440~~ 0` before every Generate click, never varied.

## Filing

Nothing filed to Drive — no successful render exists to file. Per the
playbook's "whatever the verdict, it is filed" rule this would normally
apply to a rendered-but-rejected clip's info, but here there is no clip file
at all (no output video was produced by any of the three copyright
rejections — the platform never generates output for a copyright-blocked
job).

## Recommendation for next pass

Since the previz-label theory is now ruled out and the name is already
stripped, the next diagnostic step is narrowing which reference or prose
detail in the paste block is triggering the filter — likely candidates:
`@project_absence_prop_croc_bag` (a real luxury-brand-adjacent handbag
description: "structured top-handle, polished deep OXBLOOD crocodile, gold
clasp" reads close to a recognizable designer silhouette), or the room
reference `@loc_hall_big_e` / cast descriptions themselves. Recommend CTO/CEO
review which Element plate might be flagging, ideally by testing the prompt
with one described prop/character swapped for a genuinely generic
placeholder, one variable at a time, rather than another blind unchanged
re-fire.
