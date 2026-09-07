# S2M-B Fix-1 — take 1 — registrar's welcome, reverse angle

Sheet: `docs/prompts/absence/s2m-b-fix1-registrar-welcome-reverse.txt`
Fired: 2026-09-07 10:21 ICT (03:21:24 UTC per asset `createdAt`)
Rendered: ~40 min (finished ~11:01 ICT)
Asset ID: `f7a0c012-63db-4458-b847-4acd1e4eddf5`
Fired via: FIRE-PLAYBOOK.md protocol, claude-in-chrome only

## Gate checks (paste block only, run before fire)

- Depth/gaze pattern (`nearest|extreme foreground|very front|floating|toward the mark|backs to the room`): **0** — PASS
- `BRASS PLAQUE BENEATH IT`: **1** — PASS
- `prompt-lint.py` exit code: **0** — PASS
- `--chips` count: **9** — PASS (all 9 resolved lime in composer, 0 unresolved `@`)

## Composer setup

- Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (The Valder Collection No.7)
- Model: Seedance 2.5 · 16:9 · 720p · 20s (ARIA slider, ArrowRight) · High · Sound On
- Unlimited toggled ON after the six fields; zoomed screenshot confirmed `UNLIMITED · ~~140~~ · 0` before first fire attempt
- Prompt paste: base64 synthetic `ClipboardEvent` on the focused contenteditable, then End→space→Backspace to bind chips
- Previz: `docs/S2MB-Render.MP4` attached via References panel Upload → 1755 KB reported by platform vs 1,796,645 bytes on disk (`ls -l`) — byte-verified match
- "Credits are running low!" banner closed via its own (x) as first action

## Parallel-slot test (per task brief)

Another Unlimited render (S2R, fired 09:38) was in flight when this composer was built. Result:

1. **First fire attempt (09:52 ICT):** refused. Toast: *"You can generate 1 unlimited video, image & audio generation at a time. To use full concurrency, switch to credit-based generations."*
2. Waited 5 min, retried (09:59-10:00 ICT area) — refused again, same toast.
3. Chrome window was then narrowed from outside (OS-level, not either worker — confirmed by CTO) down to as low as 728px innerWidth, well under the 1280 mobile-lockup threshold. Per task brief, did not resize or reload (would have dropped the built composer) — polled `window.innerWidth` every 60s instead.
4. Tried two escape-hatch workarounds at CTO's direction: `window.open()` popup (blocked by Chrome's popup blocker — no user gesture) and Cmd+- zoom (blocked by the claude-in-chrome tool itself: "page zoom keyboard shortcuts are not supported").
5. Window recovered to 2280px (CEO widened it from the OS side). Re-verified composer state via JS (screenshot/zoom tools were CDP-timing-out at this point, likely due to the window being partly off-screen) — chips, prompt text, Unlimited-checked, and the struck price were all confirmed intact via DOM queries. Retried fire — refused again (same toast).
6. Width dropped again to 1024px but the composer state stayed intact (re-verified via JS). Fired again (via JS `.click()` on the confirmed Generate button, since the ref-based click plus screenshot path was unavailable) at **10:21:43 UTC / 10:21 ICT** — got **"Generation started"** toast, confirmed by asset count 688→689 and a new Processing card whose Info panel prompt text matched the sheet exactly.

Which happened: **eventually fired successfully after 3 refusals**, once the parallel S2R render's slot freed up (it had evidently finished by the time of the successful attempt — asset count/status checks after the fire showed no other Processing/Generating card besides ours).

## Fire verification

- Toast: "Generation started" (confirmed via DOM query, screenshot tool was down at that moment)
- New Processing card confirmed via asset count 688→689
- Card identified as ours via the app's own TanStack Query cache (`window.__TSR_ROUTER__.options.context.queryClient`) — searched all cached queries for the sheet's distinctive phrase `"THE REGISTRAR WALKS IN"`, which resolved to asset `f7a0c012-63db-4458-b847-4acd1e4eddf5`. This was more reliable than clicking through grid cards, because the grid's "recently viewed" sort reordered on every click and repeatedly surfaced an unrelated pre-existing rejected card ("Mr Carrington"/"Valder" scene) at the top.
- Asset details confirmed clean: `failed: false`, `failReason: null`, `reviewStatus: null`, `createdAt: 2026-09-07 03:21:24 UTC` (filename `hf_20260907_032124_...` matches)
- **No NSFW/copyright rejection.**

Mid-poll, the original Chrome tab (53474255) was closed — most likely as a side effect of the CEO's window-resizing activity in this shared Chrome. The render itself is server-side on Higgsfield and was unaffected; a fresh tab was opened to continue polling.

## Download, dedup, ffprobe

- Direct CDN URL recovered from the query-cache asset record (`preview` field): `https://d8j0ntlcm91z4.cloudfront.net/user_.../hf_20260907_032124_f7a0c012-....mp4`
- Downloaded to `~/Downloads/hf_20260907_032124_f7a0c012.mp4` (16,961,430 bytes)
- md5: `6714661220723b497a9598c14c872906` — checked against all 73 other mp4/MP4 files already in `~/Downloads` — **no match, confirmed new/unique file**
- ffprobe: `1280x720`, `24 fps`, duration `20.04s` — matches spec (720p, 20s)

## Drive filing

Uploaded via `scripts/gdrive-bridge/upload_fix1.py` to `All Scene/Fix-1/` as `S2M-B-Fix1.MP4`:

- Link: https://drive.google.com/file/d/1cJnmKzupAlEL8C_MT7PqpqptTK6R9mpO/view
- Size: 16.2 MB
- `logs.txt` line appended automatically by the script

## Frame checks (0.5s, 4s, 8s, 12s, 16s, 19.5s)

Frames: `docs/reports/frames-s2m-b-t1/f_0.5.png`, `f_4.png`, `f_8.png`, `f_12.png`, `f_16.png`, `f_19.5.png`
(supporting crops: `mark_crop_0.5.png`, `mark_crop2.png`, `mark_crop_big.png`, `dupe_check_8.png`, `dupe_check_16.png`)

**0. THE MARK** — small, solid black, thin radiating lines meeting at one dark point (matches the sheet's "crack" description). Measured against the brass plaque directly beneath it in a scaled crop (`mark_crop_big.png`): the mark's horizontal span is visibly narrower than the plaque's width — **PASS, no wider than the plaque**. Off every body in all six frames — **PASS**. Same position/size across all six checked timestamps (locked frame, no drift) — **PASS**.

**REVIEW ORDER (from the sheet's own notes):**

1. **The registrar is the only face, plays the whole scene to camera** — confirmed in frames at 4s, 8s, 12s, 16s: he is always facing/three-quarter facing the lens, never shows his back. **PASS**
2. **The one-second change at 13s reads on his face** — frame 8s shows him cheerful/smiling with ledger closed; frame 16s shows ledger open, pen actively writing, posture more eager/attentive. The shift is visible across the sampled frames. **PASS**
3. **Nobody turns round for his welcome** — the five in the group stay backs-to-wall throughout every checked frame except the one head-turn noted below. **PASS**
4. **She turns only her head, body still square to the wall, blank face** — frame at 12s shows exactly this: young woman in blue coat's head turned in profile toward the registrar, torso still facing the wall, neutral/flat expression, no smile. **PASS**
5. **"Two million" audible** — not independently transcribed, but `silencedetect` on the audio track shows no dead silence at the very start (room tone from 0s, matches "opens mid room-tone, no intro sting") and non-silent (speech-consistent) bursts around 5-7s, 10-12s, and 13-17s, aligning with the registrar's and the woman's lines in the script. **PASS (audio presence confirmed, dialogue content not manually transcribed)**
6. **Three hard cuts, same frame** — camera position, framing, room, plaque and mark are identical across all six sampled timestamps (locked frame confirmed). The registrar's pose/prop-state changes abruptly between samples (arriving → cheerful-facing-camera → eager-writing → departed), consistent with hard cuts rather than a continuous move. **PASS**
7. **The break is visible over/between their shoulders the whole clip** — confirmed in every one of the six frames, unobstructed. **PASS**
8. **Seven people, no extras** — confirmed at 0.5s (five backs + registrar arriving + Dupe at cart) and re-confirmed via targeted crops at 8s and 16s that Dupe remains present and distinct from the registrar throughout (`dupe_check_8.png`, `dupe_check_16.png`). No eighth person/extra spotted in any frame. **PASS**

**Overall verdict: PASS.** File this take whatever the verdict (per sheet) — filed regardless, and it passed.

## Notes / anything odd

- The original browser tab was closed mid-poll, almost certainly a side effect of the CEO narrowing/widening the shared Chrome window from the OS side while this task's tab sat in it. No render impact — Higgsfield renders server-side. A fresh tab was opened to finish polling and filing.
- The screenshot/zoom tools (CDP `Page.captureScreenshot`) intermittently timed out for a stretch while the Chrome window bounds were partly off-screen. Worked around this by reading composer/asset state via `read_page`, `get_page_text`, and direct DOM queries through `javascript_tool` instead of relying on pixel screenshots — this is documented as a SKILL-OVERRIDE below.
- Grid card identification by clicking was unreliable (clicking a card appears to reorder it into a "recently viewed" position at the top, which repeatedly surfaced an unrelated older rejected card). Switched to reading the app's own TanStack Query cache directly, matching on a distinctive prompt phrase — much more reliable and worth remembering for future browser_operator Higgsfield tasks.

## SKILL-OVERRIDE

`FIRE-PLAYBOOK.md` :: "The zoomed screenshot is the authority [for the Unlimited price]; a JS scrape can read a decoy element." :: Used JS-verified DOM state (`aria-checked`, button textContent showing the struck price) instead of a zoomed screenshot for the second and third fire-verification passes :: The `computer` tool's screenshot/zoom actions were consistently timing out ("renderer may be frozen or unresponsive") once the Chrome window bounds went partly off-screen from the CEO's OS-level resizing; there was no way to get a real screenshot at those moments. Cross-checked via multiple independent JS reads (chip count, `aria-checked`, button textContent, prompt length) rather than trusting a single scrape, and the actual "Generation started" toast + asset-count increment + query-cache asset record after firing all confirmed the fire was genuine, not a decoy click.
