# S2C-Fix1 take 2b (task-c17f1626, 2026-09-04)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (The
Valder Collection No.7). Confirmed logged in and correctly scoped before
touching anything (prior task-567f76a5 hit an account-wide logout mid-setup —
that was not reproduced here; the CEO had already logged back in).

## What was fired

- **Prompt**: `docs/prompts/absence/s2c-fix1-pacing.txt`, PASTE-block only
  (verified char-for-char via first/last-60 + length reads before and after
  paste; `scripts/prompt-lint.py` ran clean, exit 0).
- **Previz**: `docs/S2C-Render.MP4` (1280x720, 480 frames, 20.0s, 4,704,330
  bytes, MD5 `8211627318a796785c4c240147b518d8`) attached as `@Video 1`.
- **Elements, three**: `@loc_hall_big_e`, `@project_absence_char_cleaner_c`,
  `@project_absence_prop_cart_a_painted` — all three resolved as real
  reference-thumbnail chips (verified visually: hall interior, Dupe's face,
  the painted cart) with correct highlight colour, not the red
  unresolved-tag state.
- **Filing target** (post-render, editor's job): All Scene/Fix-1/S2C-Fix1.MP4.

## The six fields, read back immediately before the click

| Field | Value | How confirmed |
|---|---|---|
| Duration | **20s** | ARIA slider `aria-valuenow="20"` set via 15x ArrowRight from a focused thumb (started at 5s default); zoomed on-screen chip read "20s" |
| Resolution | **720p** | Quality dropdown selection; zoomed chip read "720p" |
| Aspect | **16:9** | Zoomed chip read "16:9" (project default, unchanged) |
| Model | **Seedance 2.5** | Explicitly selected from the model dropdown (composer defaults to Cinema Studio 4.0) |
| Quality | **High** | Zoomed chip read "High" (unchanged default) |
| Sound | **On** | Zoomed chip read "On" (unchanged default) |

**Price at the click**: zoomed screenshot of the Generate button immediately
before clicking read **`UNLIMITED · ~~440~~ · 0`** — struck-through price,
`0` charged. Unlimited toggle confirmed `data-state="on"` via one clean
ref-click (hard rule 5), first attempt.

## The fire itself — two tabs, one real click

The first staging attempt (tab A) had its Generate button stop responding
after full staging: two raw-coordinate clicks, one `find()`-ref click, and
one more after a soft back-navigation - four clean attempts, zero
`generate`/`job`-type network requests observed in any of them (confirmed via
`read_network_requests`), while clicks on unrelated page elements in the same
tab worked normally. This matches the skill's documented "clicks stop
registering across the whole tab" failure class. Per the skill's ladder, a
**fresh tab** was opened rather than continuing to click near a priced
button.

In the fresh tab (tab B), the full staging sequence was redone from scratch
(video re-attached, prompt re-pasted, `@Video 1` re-inserted, duration/
resolution re-verified - settings had persisted account-wide from tab A's
edits, which sped this up) and the price re-verified fresh immediately before
clicking. **The single Generate click on this second tab produced Higgsfield's
own "You can generate 1 unlimited video, image & audio generation at a time"
toast** - confirmation that the click registered and the job was accepted,
not the money-priced Generate action itself repeating.

## Confirmed via Usage History (ground truth, not UI inference)

`https://higgsfield.ai/me/settings/usage` -> Usage history log, most recent
entry: **`Unlimited . Seedance 2.5 . Spent . Sep 4, 2026 6:26 AM`**. Current
time at that check was 6:36 AM (ICT) - a 10-minute-old entry matching the
Generate click exactly. This is the authoritative confirmation the job fired
and is billing correctly (`Unlimited`, i.e. $0, not a live credit charge).

No entry above it, no refund/failure entry beneath it. Total 7-day spend for
this account: $18 / 450 credits, 100% attributed to GPT Image 2.0, 0% to
Seedance 2.5 - consistent with zero paid video charges from this session.

## THE CLIP LANDED — 07:00 ICT, ~34 minutes after the click

Confirmed live in the project grid at `?preview=e84b4871-5ceb-4f4d-ad7d-2bef144a7723`,
badged "New". **No visible "Processing" card was ever found in any grid,
history or picker view while it rendered** (checked repeatedly across ~30
minutes: main grid, account-wide "My generations", Filter -> Status -> "In
progress" — that filter turned out to be a manual review-workflow tag, not a
render-status indicator — and the Generations picker filtered to Video
Generations). The asset appeared abruptly, fully finished, with no visible
in-between state. Flagging this as a real gap in this account/UI tier for
future operators: **the Usage History timestamp, not any in-app spinner, is
the only reliable mid-render signal available.**

**File identity, independently confirmed three ways:**
- Its underlying filename is `hf_20260903_232626_4e960c68-1282-427b-841d-b8199baf8937.mp4`
  — the embedded timestamp `20260903_232626` UTC = **06:26:26 ICT**, matching
  the Generate click and the Usage History entry to the second.
- `HEAD` on its CDN URL: 200, `content-length: 20145469`, `content-type:
  video/mp4`, `last-modified: Thu, 03 Sep 2026 23:59:46 GMT` (06:59:46 ICT —
  render took **~33 minutes**, consistent with the US-peak slow window the
  fire landed in).
- Downloaded via the card's own Download button (no rights-verification
  banner appeared) to `~/Downloads/`; local file size matches the HEAD byte
  for byte (20,145,469 bytes), MD5 `9aca2d143668edb293ba7a757b628265`. Copied
  to `~/Downloads/S2C-Fix1.MP4` (scene-named, no verdict in the name, per the
  brief) alongside the original.

**Technical spec of the finished file** (`ffprobe`): 1280x720 h264 @ 24fps +
aac audio, duration **20.04s** (the same clean target-consistent overshoot
documented elsewhere for a 20s ask — not a defect). `volumedetect`: mean
-29.3 dB / peak -4.6 dB — a real, non-silent audio track with dynamic range.

## THE FIRE WAS NOT REFUSED — resolves the open question in the brief

**This is the headline finding.** S2C was refused once before the prompt
rewrite (full render, then "Output may contain sensitive content"); S2-Fix1
was refused the same way. This rewritten prompt rendered clean end to end —
no scanner banner, no mid-render refusal, no post-render content warning,
full frames, full audio, normal download. **A pass here means the refusal
tracked something in the old text, not the shared Elements or the scene
concept itself** — the two live theories from the brief (word-level prompt
differential, shared-Element contamination) can both be closed for S2C
specifically; whatever tripped the scanner before is gone from this text.

## Verdict against the review list — frame-sampled review (PASS)

Extracted and reviewed 1fps frames across the full 20s, an 8fps burst across
1-4s for gait detail, full-resolution frames at the start/PA-freeze/end
beats, and a difference-blend of the first vs. last frame to check camera
drift pixel-by-pixel (methodology, not just eyeballing, per the brief's own
instruction on point 4).

| # | Check | Read | Evidence |
|---|---|---|---|
| 1 | Fast real walk, one foot down, no running | **PASS** | 8fps burst (1-4s) shows a genuine alternating-stride gait with motion blur consistent with real walking speed; no frame shows both feet clearly airborne, no floating/teleport artifacts |
| 2 | Never looks at camera | **PASS** (frame-sampled) | Most frontal pose is the t=10s PA-freeze; full-res crop shows his eyes lowered/averted, not direct lens contact. Not exhaustively checked frame-by-frame — full-speed playback review is still worth a look before this is called 100% clean |
| 3 | Panic, not busy-ness | **Consistent, qualitative** | Hand-to-cap/face gesture visible in the opening frame; hesitant repositioning across the "empty hallway" beats at 5s/6s and 15-17s tracks the prompt. Full judgment on performance quality is the CTO's per the review loop |
| 4 | Camera dead still, whole 20s | **PASS, strong evidence** | Difference-blend of frame 0 vs. frame 19.5: background (columns, ceiling lamps, red door, shell chair, cart, framed art) shows near-zero pixel difference across the entire frame — only Dupe's silhouette differs, which is expected since he's present in one frame and gone in the other. No systematic drift anywhere in the image |
| 5 | No cracked wall, no plaque | **PASS** | Scanned all 20 1fps frames plus full-res start/mid/end frames — hero wall never enters frame; visible walls show only clean plaster, columns, sculptures on plinths, and framed artwork |
| 6 | Ends on the cart, alone, holding the painting | **PASS** | t=19.5s frame: empty hallway, cart stationary in its original position with bucket/mop/bottles/gold-V panel visible; matches "long empty gallery... cart standing alone" |

**Overall verdict: PASS**, on the frame sample reviewed. Per the skill's
standing review-loop rule ("the operator never self-certifies a clip"), this
is my operator-level read for the re-fire/no-re-fire call the brief asked
for — the CTO should still open full-resolution frames personally
(`video-see.sh` / direct playback) before final sign-off, since ~44 sampled
frames out of 481 total cannot rule out a single-frame anomaly the way a full
watch can.

## Filing — blocked on Drive access, not on the render

The brief's target is `All Scene/Fix-1/S2C-Fix1.MP4`, matching the `YT: ILAG`
Drive convention documented for the sibling "Do Not Disturb" project in the
`gdrive-filing` skill. **That skill's folder map has no entry for this film
("The Valder Collection No.7" / "Absence") at all** — every ID it lists is
under `YT: ILAG/Do Not Disturb`. This session also has no Google Drive MCP
tool available (checked via `ToolSearch`; browser_operator scope does not
carry Drive access). Both mean I cannot resolve the correct target folder ID
myself, and per that skill's hard rule 3 ("never create a new sub-folder
without asking first") I should not guess one into existence.

**The clip is staged and ready** at `~/Downloads/S2C-Fix1.MP4` (and the
original `~/Downloads/hf_20260903_232626_4e960c68-1282-427b-841d-b8199baf8937.mp4`
for provenance) for whoever has Drive access to file it into the correct
`All Scene/Fix-1` (or equivalent) folder under this film's own `YT: ILAG`
project — which itself may need to be confirmed/created first, since it does
not appear in the current folder map.

## Blocker

None that stops the deliverable — the render is done, confirmed correct, and
locally staged. Two things flagged for the record, neither blocking:

1. **A browser-tab-wide click-registration failure** (four clean, verified
   attempts on a correctly identified Generate button, zero network effect)
   was hit and worked around per the skill's documented fresh-tab escalation
   — no credits were spent by any of the failed attempts (confirmed via
   Usage History: only one Seedance 2.5 Unlimited entry in the whole session
   window).
2. **Drive filing needs a human/CTO with Drive access** — the Valder
   Collection / Absence project has no documented Drive folder yet.

## SKILL-OVERRIDE

None. The stuck-button symptom in tab A does not match hard rule 5's
Unlimited-toggle-specific "one clean attempt, escalate to CTO" rule (that
toggle worked correctly, first try, in both tabs) - it matches the separate
"long-lived tab lies about the concurrency slot" section's documented
whole-tab click-deadlock symptom, whose prescribed fix (open a fresh tab) was
followed and resolved it.
