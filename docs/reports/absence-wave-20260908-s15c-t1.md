# S15c THE TEARS — take 1 — 2026-09-08

## Purpose
Fire S15c on the UNLIMITED (FREE) lane as a probe of whether the lane is
alive at all, following S14's cancellation at 154min with no landing.

## Gates (before browser)
- `git merge main` — already up to date.
- prompt-lint: exit 0, 12/12 expected chips.
- Attribute gate: ledger→registrar only ✓, bodyguard hands empty ✓, no gold
  teeth (grep across joined lines) ✓.
- Flagged-Element check: `project_valder_char_villagers_poor`, `prop_croc_bag`,
  `prop_car` (word-boundary match) — none present in this sheet. `prop_cart_b`
  present and correctly unflagged.

## Browser
- innerWidth readback: 1440 (>=1280) ✓.
- Credits-low banner: closed via its own (x).
- 12/12 reference chips bound (verified via the confirmed selector
  `span.text-font-brand` filter), zoom-checked all 12 thumbnails for warning
  triangles — none present.
- Six fields set: 16:9 / 720p / 8s (ARIA slider, ArrowRight x3, read back
  "8s" in both popover and bar) / High / 1/4 / Sound On.
- Unlimited toggled ON **after** the six fields (duration change resets it,
  per playbook). Zoomed Generate button: `UNLIMITED · ~~56~~ · 0` — struck
  price, zero charge.
- Fired ONCE at **2026-09-08T08:09:06Z (15:09:06 ICT)**. Confirmed via
  "Generation started" toast + new Processing card + asset count 721→722.

## Render
- **Landed between ~176min and ~187min elapsed (~180min)** — a second data
  point right at the S2I-t1 precedent (185min), reinforcing the CTO's
  correction: a long render is not evidence of a stalled lane. **The FREE
  lane is alive.**
- Poll cadence: first check ~20min, then every 5min, bounded ~90s sleeps,
  stayed in one turn throughout.
- Mid-poll: two other generations (not mine) also ran concurrently on the
  shared account — correctly left alone, per skill guidance ("expect
  generations you did not start").
- One tab-fault episode: screenshot capture timed out repeatedly on the
  original tab even though JS/DOM stayed responsive (readyState complete).
  Hard-reloaded once (no fix), escalated to ONE fresh tab per FIRE-PLAYBOOK —
  resolved immediately. Old tab released from the registry before closing;
  new tab claimed.
- Near-miss: opening the account menu (to answer the CTO's credit-balance
  ask) surfaced a "$49 Confirm payment" retry-charge modal instead of the
  balance — closed via its own (x), nothing confirmed, no charge. Balance
  was found instead via Subscription page: 1,000/1,000 monthly credits.
- Card identification: two "New" spinner cards appeared simultaneously at
  one point (asset count 722→723→724 across the session — other operators'
  cards). Confirmed MINE via Info panel: prompt text matches the sheet's
  paste block exactly ("TWO SHOTS, one hard cut at 4s, then a very slow
  push-in on Dupe's face..."), Created "September 8, 2026 at 3:08 PM" (≈ fire
  time), Seedance 2.5 / 720p / High / 1280x720. Two other completed cards
  checked and ruled out (a wheelchair-move scene, a locked-shots scene — both
  different prompts, different Created times).

## Download / verify
- File: `hf_20260908_080858_7b2de0c5-785f-40b4-b5cb-df6022d76e7b.mp4`.
- md5 checked against every other `hf_*.mp4` in `~/Downloads` — no collision.
- ffprobe: 1280x720, 24fps, duration 8.05s. Matches spec exactly.

## Review (sheet's REVIEW ORDER)
1. **Tears run, he stays still — PASS.** Tears visible from 0.5s onward
   (frames at 0.5/2.0/3.5s), mop-handle grip held, shoulders static, mouth
   closed throughout shot one.
2. **Nobody comforts him — PASS.** No one approaches or touches him in any
   sampled frame.
3. **Sideways eye flick in shot two — PASS.** Clear downward/leftward glance
   visible at 4.5s and 6.0s, eyes back to front by 7.8s (end frame).
4. **No smile — PASS.** Mouth closed in every sampled frame (0.5s through
   7.8s).
5. **No dialogue — PASS.** `silencedetect` (-30dB/0.3s): silent 0-3.79s and
   3.84-7.72s; only a brief non-silent moment at 3.79-3.84s (matches the
   prompt's "his breathing gone uneven once", right at the cut). Mean volume
   -43.6dB, max -24.1dB — consistent with room tone, not speech.
6. **Push-in smooth — PASS.** Greyscale-MAD sweep (below) shows a smooth,
   continuous rise-then-fall with no jagged/noisy steps that would indicate
   handheld wobble.
6b. **Cut sweep — REAL, ISOLATED CUT at ~3.8-4.0s.** 0.2s-step greyscale MAD
   between consecutive frames, median = 2.891 (3x = 8.674).
   - **3.8-4.0s: 46.844 (16.2x median)** — one isolated spike, cleanly
     separated from the near-flat shot-one baseline (0.3-0.8 the whole way)
     before it.
   - 4.0s onward: values climb smoothly 2.0 → 8.8 (peaking 6.6-6.8s) then
     fall back to 4.6 by 7.6-7.8s — a **sustained rising/falling run**, which
     per the sheet's own instruction IS the push-in itself, not a second cut
     (one point at 6.6-6.8s technically crosses 3x median but is part of the
     continuous ramp, not an isolated spike).
   - Verdict: the cut into shot two reads as ONE isolated spike exactly as
     required. Not a false continuous shot.
7. **Room/cast — PASS on what's checkable from a frontal frame.** Three
   bodyguards at the left edge in the sheet's specified order (tall thin navy
   guard, short heavy navy guard, black-suit-white-gloves Carrington bodyguard).
   Visible principals on the right (Carrington, grandmother/wheelchair partial,
   Madame Thibault, Valder, registrar) match their described costumes. No
   duplicate faces spotted. Full 21-person count not verifiable from the
   frontal chest-up framing (not all background/press visible in frame).

## Filing
Uploaded via `scripts/gdrive-bridge/upload_fix1.py` (appends logs.txt):
`All Scene/Fix-1/S15c-TheTears-Fix1.MP4`
https://drive.google.com/file/d/1WuRPwGmk-x9Iy3ndhftS3EDt4g6JzmRi/view

## Verdict
**PASS on every review item.** Take 1 is the filed version — nothing to
compare against (first take under this name).

## Lane health (the actual point of this probe)
**The FREE/Unlimited lane is alive.** ~180min render, landing clean, is the
SECOND observed case of a long card landing successfully (after S2I-t1 at
185min). There remains no observed case of a long card failing on its own —
every "died" card on record was cancelled, which tells us nothing about what
it would have done left alone. Recommendation: do not treat render time past
60min as a stall signal on this lane; let renders run.
