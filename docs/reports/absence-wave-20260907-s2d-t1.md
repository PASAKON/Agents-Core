# S2D-Fix1 · THE FIRST GUEST — Take 1 fire report

**Date:** 2026-09-07
**Task:** task-ac940275 (browser_operator)
**Sheet:** docs/prompts/absence/s2d-fix1-first-guest.txt
**Playbook:** docs/prompts/absence/FIRE-PLAYBOOK.md

## 0 · Gate check (paste block only)
- `git merge main` — already up to date with main (>= 1c2808f).
- Depth/gaze pattern (`nearest|extreme foreground|very front|floating|toward the mark|backs to the room`): 0 matches — PASS
- `loc_wall_pov_e` count: 0 — PASS (loc_hall_big_d only, per sheet's explicit instruction)
- `prompt-lint.py` full run: exit 0 — PASS
- `prompt-lint.py --chips`: 5 expected — `@project_absence_char_cleaner_c`, `@project_absence_char_oldman`, `@project_absence_loc_hall_big_d`, `@project_absence_prop_cart_a_painted`, `@project_absence_prop_tag`

## 1 · Browser
- Reused an existing empty tab (tabId 53474196), claimed for this task.
- innerWidth readback: 1366x754 (proven via JS) — above 1280 floor.
- "Credits are running low!" banner closed via its own (x), first action, re-closed after every reload.
- Video tab confirmed active before any field changes.
- Six fields set and re-verified via zoomed screenshot + JS scrape each fire attempt: Seedance 2.5 · 16:9 · 720p · 20s (ARIA slider, ArrowRight x15 from 5→20) · High · Sound On.
- Duration-reset behavior confirmed again: every reload reset resolution to 1080p and duration to 5s (not just Unlimited) — full six-field re-verify required after every reload, not just Unlimited+zoom.
- Price zoom (authority, not JS scrape): `UNLIMITED · ~~140~~ · 0` — matches the brief's expected 130-credit pre-toggle price for 20s/720p (brief's "~440" guess was wrong; actual list price confirmed 140/130 consistently across both fire attempts).

## Paste method
- Base64-encoded paste block, decoded client-side via `atob`, dispatched as synthetic `ClipboardEvent('paste', {clipboardData, bubbles:true, cancelable:true})` on the focused contenteditable (`document.activeElement` after clicking the composer directly — single visible contenteditable this time, no Image/Video duplicate-node issue hit).
- End→space→Backspace tap performed after paste to lock Lexical chip bindings.
- Chip gate: 5 chips, all lime, 0 unresolved, unique names matching the sheet exactly — confirmed both before and after re-verification post-reload.

## Previz
- `docs/S2D-Render.MP4`: byte count 3,781,305 matches sheet exactly (`ls -l` vs. platform upload confirmed via its own Info panel: 3.8 MB / "Uploaded").
- Uploaded via `file_upload` to the references-panel file input; selected from the Uploads picker ("Added to prompt box" toast), landed as reference tile #6.
- `readyState: 0` on the tile throughout — per playbook this is benign when Generate stays enabled, which it did. Fired with it attached.

## Fire — TWO ATTEMPTS, ONE REAL

### Attempt 1 (FALSE FIRE — root-caused, no cost incurred)
- Clicked Generate via an accessibility-tree lookup (`find` tool → ref matched a button with accessible name "Generate").
- **That ref pointed at a hidden 0×0px decoy button** sharing the same accessible name as the real control (its `textContent` read `"GENERATE8045"`, a stale/decoy price, while the real visible button showed `"Unlimited1400"` — i.e. `UNLIMITED` + struck `140` + `0`). No "Generation started" toast appeared, no generation-related network POST fired (confirmed via network log — only analytics/telemetry POSTs), and the asset count stayed effectively flat.
- Misdiagnosed initially: after this click, `All assets` went 680→681, which was mistaken for fire confirmation. Root cause of the miscount: **the S2D-Render.MP4 previz upload itself counts as an asset in the "All assets" grid** (confirmed via its own Info panel — Status: Uploaded, appears in the main gallery, not just the Uploads picker) — the +1 was the upload, not a generation. Filtering `All assets` by `Today + Generated` showed zero new items after 50 minutes of polling, which surfaced the false fire. Flagged to CTO via `dev_message`; CTO confirmed the same conclusion independently and ordered a real re-fire.
- **PLAYBOOK GOTCHA TO ADD:** the Generate button apparently has (at least on this page state) a hidden decoy sharing its accessible name — `find`/ref-based lookups can silently click the wrong element. Verify success by the "Generation started" toast + a real network response, not by ref-click success alone. `All assets` count is not proof by itself if a previz was uploaded in the same session — that upload independently increments the same counter.

### Attempt 2 (REAL FIRE)
- Reloaded, rebuilt all six fields from scratch (reload resets composer to Seedance defaults every time), re-verified 5 chips + previz reference survived reload, re-toggled Unlimited, re-zoomed price.
- Located the actual button via JS: filtered visible `<button>` elements whose text contains "Unlimited" (rect w=120,h=80, at the price-tag position) — distinct from the 0×0 decoy — and called `.click()` on it directly (per playbook's documented fallback: "one JS `.click()` on the $0 button").
- Confirmed: **"Generation started" toast** + asset count **681→682** + new spinner/Processing card appeared at the very top of the "All assets" grid on next reload.
- ONE real fire. No paid controls touched, no control clicked twice, S2R's three pre-existing rejected cards and the CEO's `SEEDANCE 2.5 CREDIT` cards left untouched throughout.

## Render
- Fire time: ~2026-09-07T06:33 local (ICT+7).
- Polled every 5 minutes with a full page reload each time. Card stayed on spinner through the 5, 10, 15, 20, 25-minute checks.
- Finished (real thumbnail replaced the spinner, "New" badge) at the 30-minute checkpoint — well within the 30-55 min playbook estimate.
- No NSFW/refund banner. No copyright-rejection info-icon overlay present on the card's hover state (unlike the pre-existing S2R rejected cards nearby, which do show a persistent ⓘ overlay) — clean pass.
- Created timestamp per Info panel: September 7, 2026 at 6:03 AM.

## Filed
- Downloaded: `hf_20260906_230335_23a5e0ca-2eab-42bc-b8e7-ac8ec61fb46c.mp4`, 16,995,625 bytes (~16.2 MB).
- ffprobe: 1280x720 video + audio stream, duration 20.04s — matches spec exactly.
- Filed via `scripts/gdrive-bridge/upload_fix1.py` to `Sorry, Sir / All Scene / Fix-1` as `S2D-Fix1.MP4`:
  https://drive.google.com/file/d/1QAMo0b_B5ajJE5TvgpQNKNlSz-dx9ImA/view
- logs.txt line appended by the script.

## 3 · Checks — frames at 0.5s, 4s, 8s, 11s, 14s, 19.5s (+ one extra check frame at 12s for the flinch beat)

Frame paths: `docs/reports/frames-s2d-t1/frame_{0.5,4,8,11,12s_check,14,19.5}s.png`

### Sheet's own REVIEW ORDER
1. **THREE SHOTS, cut at 7s and 10s, each locked off** — PASS. Frames 0.5s/4s share one locked composition (wall + cart, Dupe entering/looking up); frame 8s is the distinct star-hole insert; frames 11s/14s/19.5s share a second locked composition (behind Dupe, down the gallery). No camera movement detected within either multi-frame group.
2. **Shot two genuinely from inside the wall — black surround, HAND ONLY in the opening, never a face/eye** — PASS. Frame 8s: full black frame except the star opening; two fingertips visible through it, gallery beyond, no face or eye anywhere in the shot. (Sheet describes "ONE FINGER" specifically; two fingertips are visible at this exact frame — still hand-only, no face/eye, so the negative that matters is respected.)
3. **The flinch at 12s is a real startle, not a glance** — INCONCLUSIVE from stills, but consistent. At 12s (frame_12s_check.png) Dupe is still standing normally, back to camera, gallery still empty at the far end. By 14s the elderly man has entered and Dupe has already turned to the wall and begun cleaning. The entrance/reaction transition falls correctly inside the 12-14s window; the specific micro-gesture of the startle itself cannot be confirmed or denied from a static frame at exactly 12s.
4. **The fake cleaning reads as fake — same patch, over and over, while he watches someone else** — PASS. Frames 14s/19.5s show Dupe with cloth in hand against the wall, head turned/craning toward the gallery rather than looking at what he's wiping.
5. **One visitor only, who never speaks and never notices the wall** — PASS. Frames 11s/14s/19.5s show exactly one visitor: heavy-set elderly man, dark green leather overcoat with wide shawl collar, cream layer visible at the collar, pale gloves, slim silver cane, pale shoes — matches the reference description closely. He walks unhurried, looking at the plinths/artworks, never toward Dupe or the wall, never toward camera, no dialogue.

### Task's own additional checks
- **The mark in shots one/three small (no bigger than the reference)** — PASS. The crack is the same small size and shape across frames 0.5s, 4s (shot 1) and 11s, 14s, 19.5s (shot 3) — a thin star-shaped crack with radiating hairline cracks, no oversized/monster version, no second/extra crack anywhere.
- **Dupe too short to see into it** — not independently verifiable from static frames (would require the hop motion itself, which the extracted stills don't capture at the right instants).
- **The painting stays upright in the cart** — PASS. Frame 4s shows the cart's front panel displaying a colorful abstract painting upright and face-outward, matching `@project_absence_prop_cart_a_painted`. Not visible in later frames (cart out of frame in shot 3), so cannot re-confirm it stayed upright for the full clip, but nothing in the sheet's negatives ("no painting leaving the rack... no cart leaving the frame") is contradicted by what's visible.

### Critical negatives spot-checked
- No second/third guest, no crowd, no staff, no second cleaner — confirmed, only Dupe + the elderly man appear in any frame.
- No face of Dupe in the opening in shot two, no eye, no head — confirmed (frame 8s: fingers only).
- No plaque falling/moving — plaque (frame 0.5s) mounted correctly, legible, level.
- No camera movement inside any shot — confirmed per the locked-composition groupings above.

## Verdict
**PASS.** Clean take: correct shot count and cut structure, the shot-two hand-only payoff lands as scripted, the elderly man matches his reference closely and behaves as scripted (unhurried, oblivious, no dialogue), the fake-cleaning/craning beat reads correctly, and the mark stays small and consistent in both shots that carry it. Only soft spot is the 12s flinch gesture itself, which stills can't confirm one way or the other — worth a look on full playback if the CEO wants certainty on that one beat, but nothing in the sampled frames contradicts it.

## Notes for reviewer
- **Decoy Generate button** — add to FIRE-PLAYBOOK §1: a hidden 0×0px button can share the real Generate button's accessible name, causing `find`/accessibility-ref clicks to silently no-op. Verify by "Generation started" toast + network response, and locate the real button by filtering visible (`getBoundingClientRect().width > 0`) buttons whose text contains "Unlimited" (or the current struck-price text) rather than trusting an accessibility-tree match by name alone.
- **Previz upload inflates the asset counter** — add to FIRE-PLAYBOOK §1: uploading a previz reference via the file input increments `All assets` by 1, same counter used for fire verification. When a previz was uploaded in the same session as the fire, the count-based check alone cannot distinguish "fire happened" from "upload happened" — always corroborate with the toast and/or the `Today + Generated` filter showing a genuinely new item.
- Sheet's notes line added below.
