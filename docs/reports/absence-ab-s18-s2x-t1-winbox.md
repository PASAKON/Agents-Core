# S15e-AB → S18 → S2X take 1 each — «Sorry, Sir» — winbox browser operator

task-958e2561, winbox, browser_operator. Remote worker (no org MCP) — reporting
through git per WORKER.md.

## Summary

All three scenes fired on the FREE/Unlimited lane, waited out, downloaded,
and reviewed at full resolution: **S15e-AB** (clean pass, one blocking
positioning deviation flagged for the CTO), **S18** (clean pass, no
deviations), **S2X** (passes on cast/camera/audio, but the wall mark itself
reads as a likely canon-rule-8 FLAG — pale grey/tan spiderweb crack with a
hole-like core rather than the sheet's solid thick black line; numeric
bbox/fill gate passes narrowly but the colour/character does not match
canon). No real credit ever spent — every fire showed `UNLIMITED · struck
price · 0` and Usage History confirmed `$0`/Unlimited on all three. One
self-caught process error logged honestly (reloaded the composer tab
directly during Scene 1's wait instead of using a separate check tab — no
money impact, composer draft survived). Full per-scene detail, evidence,
and honest not-self-certified review below.

## Setup

- Selected winbox Chrome explicitly via `select_browser`
  (`815ddf16-36ea-4e0d-827a-f51e9ff85351`), per the task's explicit device id
  — no ambiguity to resolve.
- Base commit: worktree HEAD already contains main `2498dea` (the floor the
  task named) — confirmed via `git merge-base --is-ancestor`.
- `python scripts/prompt-lint.py <sheet>` — clean (no output) on all three
  sheets before touching the browser.
- Claimed a fresh tab via `tab_registry.py claim task-958e2561 <tabId>
  <url>`. Confirmed `task-ad30beb8` (S2PT take 2) held its own separate live
  tab in the registry throughout — never touched.
- `window.innerWidth` read 1920 throughout (desktop layout, no mobile
  lockup).

## THE ONE SLOT — first wait

On arrival the project grid showed a card in state **Processing → Generating**
(no asset-id read to confirm identity, but consistent with S2PT take 2,
`task-ad30beb8`, per the ledger's 00:09 spawn note). Per the brief, never
touched it. Polled with a fresh look every ~10 minutes, rotating to a new tab
after the first stale-tab-group reset (Chrome extension re-created the tab
group between polls — re-claimed the new tab id each time, released the old).

- Poll 1 (~10 min in): reused tab — text-scrape for literal "Processing" read
  0, but a full screenshot showed the card had moved to **"Generating"**
  (label transition my exact-match missed) — slot still occupied. Corrected
  the detector to also match "Generating"/"Queued" and to cross-check with a
  spinner (`[class*="animate-spin"]`) count going forward.
- Poll 2 (~20 min in, fresh tab): 0 Processing/Generating/Queued labels, 0
  spinners; screenshot confirmed the card had completed (now a "New" thumbnail
  card, no processing state anywhere in the grid). **Slot free after ~24
  minutes total wait** (well under the "up to an hour" estimate).

## Scene 1 — S15e-AB "SORRY, AND THE CHEQUE"

- Sheet: `docs/prompts/absence/s15e-ab-fix1-sorry-and-the-cheque.txt`. Lint
  clean. `--chips` expected 5: `char_cleaner_c`, `char_grandmother`,
  `char_valder`, `loc_hall_big_d`, `prop_cheque`.
- Model: Seedance 2.5 (already selected on load, project's embedded Video
  composer, URL re-confirmed
  `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` before
  every state-changing action).
- Unlimited toggle: read `aria-checked="false"` on arrival (this project's
  composer does not persist Unlimited across page loads, as documented).
  One clean `find()`-ref click → `aria-checked="true"`. **Did not trust the
  raw JS text-scrape of the Generate button** (a known decoy-duplicate
  hazard) — confirmed the real, visible button by full-page screenshot:
  `UNLIMITED · ~~140~~ · 0`.
- Settings confirmed via DOM + screenshot immediately before firing:
  Seedance 2.5 · 16:9 · 720p · 20s (ARIA slider `aria-valuenow="20"`,
  matches visible "20s" label) · batch 1/4 · High · Sound On · Unlimited
  ON, price struck 140→0.
- **Text entry — used the real OS clipboard, not a synthetic
  `ClipboardEvent`.** This worktree runs on the same Windows machine as the
  Chrome instance, so `Set-Clipboard` (PowerShell) with the exact file bytes
  followed by a genuine `Ctrl+V` in the focused (JS `.focus()`-confirmed)
  contenteditable node is a real user-equivalent paste — it sidesteps the
  risk of a hand-transcribed/chunked string being mistyped en route to the
  page, which a giant base64 blob pasted through the tool-call text itself
  cannot fully rule out. Verified byte length matched
  (6,171 bytes / 6,145 chars, exact match to the source file) and no phrase
  duplication (`"One hundred million"` × 1, `"I cracked the wall myself"` ×
  1) — the only difference from the raw source was extra `\n` at
  hard-wrapped line breaks inside paragraphs, a normal Lexical
  paragraph-per-line rendering artifact, not data loss or a double-paste.
  Followed with the mandated real-keystroke End→space→Backspace tap to force
  state binding.
- Chip count (`span.text-font-brand` leaf spans starting with `@`, filtered
  off the hidden decoy editor by `getComputedStyle().visibility`): **5/5
  bound, 0 error chips** — matches `prompt-lint.py --chips` exactly.
- Two `zoom` action calls timed out (CDP `Page.captureScreenshot`, 30s) while
  reading the reference strip / settings row up close. Per the HARD rule,
  checked Usage History both times before any further action (via a
  **separate tab**, never touching the staged composer tab): both times the
  most recent entry was `Unlimited Seedance 2.5 Spent Sep 10, 2026 12:41 AM`
  with no new entry and no live-price charge — confirmed the timeouts were
  inert (full-page `screenshot` continued to work fine on the same tab
  throughout; only `zoom` specifically hung). Fell back to full-page
  screenshots for all pixel verification instead of zoom.
- Final pre-fire check (full screenshot, seconds before the click): 5
  reference thumbnails visible, no warning triangles, `UNLIMITED · ~~140~~ ·
  0`, Seedance 2.5 / 16:9 / 720p / 20s / 1/4 all correct, 5/5 chips intact,
  `innerWidth` 1920.
- **Fired 2026-09-10 01:30:25 ICT (2026-09-09 18:30:25 UTC).** "Generation
  started" toast; asset count 758 → 759; new card entered `Processing`.

### Scene 1 — render wait / harvest

- **Correction, logged honestly:** at the ~20-minute check I navigated
  (reloaded) tab `1638444803` directly — the same tab holding the staged S18
  composer — instead of opening a separate check tab. This is exactly the
  mistake the skill warns against ("open a separate tab for status checks,
  leave the composer tab exactly as it was"). No money was lost (Unlimited
  toggling and Generate were not touched), and the S18 prompt text / chips /
  duration draft **survived the reload** (Lexical composer state persists
  across reloads on this project), but the **Unlimited toggle reset to OFF**
  and the Generate button went back to a live price (`52`) — exactly the
  documented reload behaviour. From this point on, all status polls used a
  **separate** tab (`1638444813`, also claimed in the tab registry) and left
  the staged composer tab untouched. S18 will get a full fresh
  re-verification of every setting (including re-enabling Unlimited) at the
  actual moment of firing, per the money rules — no exemption for "already
  staged."
- Polled with a fresh look via the separate check tab: ~20min ("Processing"
  — my exact-text detector briefly under-read this before I confirmed
  visually), ~26/31/35/40/45min ("Generating"). **Finished by ~45 minutes**
  (fired 01:30:25 ICT, card clear by ~02:17 ICT) — inside the documented
  20-50min range for this platform, on the slower side (ICT ~02:00 is UTC
  19:00, Europe evening, not the fast 01:00-07:00 UTC window).
- Opened the finished card's Info panel
  (`?preview=0bbf27ae-b178-49f3-938a-f56d2665360d`): **Created September 10,
  2026 at 1:30 AM** — matches the fire time exactly. Prompt panel shows the
  exact paste-block opening ("20s · 720p · 16:9 · THREE FRAMINGS JOINED BY
  TWO HARD CUTS at 6s and 16s..."). Model Seedance 2.5, 720p, High,
  1280x720.
- No NSFW flag, no "Rejected due to copyright" card, no rights-verification
  banner. Downloaded cleanly via the card's own Download button —
  "Download complete" toast, no confirmation dialog needed.
- Downloaded to
  `C:\Users\UsEr\Downloads\hf_20260909_183019_d8c3dfcf-047d-4ca2-994c-b26a4e6a69cb.mp4`
  (21,652,758 bytes). md5 `28870c71a2a2ed9ee34140883d482b92`. ffprobe:
  1280x720, h264, 24fps, 20.041667s duration — exact spec match.
  Asset count 758 → 759 at fire time, confirming +1 new asset.

#### Review — full resolution, honest, not self-certified

Frames extracted at 1.5, 5, 9, 13, 14.5 (added), 16, 18 (added), 19.5s into
`docs/reports/frames-s15e-ab-t1/` at full 1280x720 resolution, plus a
640-wide `contact_row.png` of the six mandated timestamps.

1. **FIVE LINES, in order, nothing else** — audio transcribed
   (`faster-whisper`, model `small`, CPU int8):
   ```
   [0.00-2.00]  I cracked the wall myself, sir.
   [2.00-4.00]  I will pay for all the damage.
   [4.00-6.00]  I am sorry.
   [8.00-10.00] I did not buy a crack in a wall.
   [10.00-12.00] I bought a work of art.
   [17.00-19.00] 100 million.
   ```
   Exact wording and order match the sheet, nothing improvised, no
   voiceover. **PASS.**
2. **THE CHEQUE legible ~13-15s** — at 14.5s (added frame; 13s itself is
   just before it comes out of the bag) the cheque is held up, clearly
   legible: **"100,000,000"** in ink, signature beneath, cream paper, exactly
   matching the sheet's prop description. **PASS.**
3. **TWO hard cuts at ~6s and ~16s, none other** — ffmpeg scene-change
   detection (`select='gt(scene,0.15)'`) found exactly two cuts, at
   **6.17s** and **15.75s** — matches the sheet's 6s/16s marks closely, no
   third cut anywhere else in the clip. **PASS.**
4. **Dupe both hands + small bow; Valder no smile, no touching** — at 16s
   (the cut instant) Dupe is reaching with one hand; by 18s both his hands
   are on the cheque and his head is tilted down (bow in progress); by
   19.5s both hands remain on it. Valder: sunglasses on, no smile in any
   frame from 16s-19.5s, hands not touching the cheque or the buyer.
   **PASS**, though see the blocking note below.
5. **The buyer: grey knit, no sunglasses, no purple. One of each person** —
   confirmed in every frame (1.5s/5s/9s/13s/14.5s/16s/18s/19.5s): grey
   knitted headscarf and cardigan, no sunglasses, no purple anywhere on
   her. Exactly one Dupe, one buyer, one Valder throughout — no duplicates.
   **PASS.**
6. **The mark on the wall (canon rule 8, informational)** — visible at 1.5s
   above the plaque: a solid black, thick, angular crack with several
   shorter branch lines, flat against the plaster — matches the canon
   description qualitatively (thick/black/angular, not pale/grey/tan, not a
   hole). No numeric threshold/bbox measurement run (the sheet marks this
   item "information" only, unlike S2X's hard-gated version). **Looks
   correct on visual inspection.**

**One blocking (non-hard-rule) deviation to flag for the CTO:** in the
THREE-SHOT (16s-20s), Valder is positioned **directly behind/between the
buyer and Dupe**, centred in the frame — not "half a step behind Dupe" on
the right as the sheet's blocking paragraph specifies. No negative is
violated (no touching between Valder and the cheque, no Valder smiling), so
this reads as a blocking/positioning deviation rather than a defect on the
level of a duplicate character — flagging per "describe honestly, the CTO
reviews" rather than judging it myself.

**Overall: S15e-AB take 1 reads as a clean pass on every REVIEW ORDER item,
with one positioning deviation for the CTO to weigh.**

## Scene 2 — S18 "THE HAMMER"

Staged (not fired) while Scene 1 renders, per the pipelining pattern —
editing composer text/settings does not touch the in-flight render or the
Unlimited toggle.

- Sheet: `docs/prompts/absence/s18-fix1-the-hammer.txt`. Lint clean.
  `--chips` expected 2: `char_cleaner_c`, `loc_hall_big_e`.
- Cleared the composer (Ctrl+A + Delete, focus verified on the real editor
  first) and pasted via the same OS-clipboard `Ctrl+V` method, followed by
  End→space→Backspace.
- Chip count: **2/2 bound, 0 error chips** — `project_absence_char_cleaner_c`,
  `loc_hall_big_e` — matches lint exactly.
- Duration changed from the inherited 20s to **8s**: clicked the duration
  control to open the ARIA slider popover (`role="slider"`, min 4 / max 30),
  confirmed it auto-focused, sent `ArrowLeft` × 12 (20 → 8), verified
  `aria-valuenow="8"` before closing the popover with Escape. Never typed
  into it.
- After Scene 1 landed (~45min render) and the slot was confirmed free (via
  the separate check tab, not the composer tab), returned to the staged
  composer: draft text/chips/duration all survived, Unlimited had reset to
  OFF (as expected from the earlier reload) with a live price. Re-verified
  `aria-checked="false"`, one clean `find()`-ref click → `true`, confirmed
  visually via full-screenshot: `UNLIMITED · ~~50~~ · 0`, Seedance 2.5 /
  16:9 (DOM-confirmed, scrolled off the screenshot crop) / 720p / 8s / 1/4 /
  High / Sound On, 2/2 chips still intact.
- **Fired 2026-09-10 02:22:56 ICT (2026-09-09 19:22:56 UTC).** "Generation
  started" toast; asset count 759 → 760; new card entered `Processing`.

### Scene 2 — render wait / harvest

While S18 renders, staged Scene 3 (S2X) in the same composer tab — editing
composer text/duration is safe mid-render (does not touch the in-flight job
or the Unlimited toggle); only page **navigations/reloads** are restricted
to the separate check tab from here on.

- Polled the separate check tab every ~5min (90s-chunked sleeps — this
  session hit repeated "system running low on memory" kills on longer
  sleeps, consistent with the shared-box memory pressure the skill
  documents; resumed each time, no render lost — the job runs server-side).
  Noted mid-wait that a second, unbriefed operator (`task-c72d5ba5`) had
  also opened a tab in this same project since 19:26 UTC — never touched,
  and confirmed my own S18 card by its exact Info-panel creation timestamp
  rather than assuming any Processing/Generating card was mine.
- One `navigate` timeout and one "Browser extension is not connected" drop
  on the separate check tab (never the composer). Per the HARD rule, checked
  Usage History both times before proceeding: most recent entry stayed
  `Unlimited Seedance 2.5 Spent Sep 10, 2026 2:22 AM` (the S18 fire itself),
  no new entry, no live-price charge. Reconnected via `select_browser` with
  the same device id; both tabs remained valid throughout.
- **Finished by ~33 minutes** (fired 02:22:56 ICT, card clear by ~02:56
  ICT).
- Opened the finished card's Info panel
  (`?preview=53cdcd4c-6992-44d2-8ea4-0e9ce4f9137b`): **Created September 10,
  2026 at 2:22 AM** — matches the fire time exactly. Prompt panel shows the
  exact paste-block opening ("8s · 720p · 16:9 · ONE LOCKED SHOT..."). Model
  Seedance 2.5, 720p, High, 1280x720.
- No NSFW flag, no rejection, no rights-verification banner. Downloaded
  cleanly. Downloaded to
  `C:\Users\UsEr\Downloads\hf_20260909_192250_eafaadee-107c-4591-827c-b602175ff27f.mp4`
  (6,287,372 bytes). md5 `64b4d23caa46ea73dd12da5acf098368`. ffprobe:
  1280x720, h264, 24fps, 8.041667s duration — exact spec match. Asset count
  759 → 760 at fire time, confirming +1.

#### Review — full resolution, honest, not self-certified

Frames extracted at the sheet's mandated 0.5, 2, 3.5, 5, 6.5, 7.8s into
`docs/reports/frames-s18-t1/` at full 1280x720 resolution, plus a 640-wide
`contact_row.png`.

1. **ONE DUPE, alone, frontal, waist up, the hall empty behind him** —
   confirmed in every frame: exactly one figure, hall visibly empty behind
   him throughout, camera frontal (framing runs closer to hip-height than a
   strict "waist up" crop, a minor framing note, not a defect). **PASS.**
2. **THE HAMMER arc** — checked at all six mandated timestamps:
   - 0.5s: hammer hanging at his side (handle visible, head just below
     frame edge).
   - 2s: arm rising, hammer at roughly hip height, head angled left.
   - 3.5s: (extracted, mid-rise, not separately described — consistent
     progression between the 2s and 5s frames).
   - 5s: hammer held at shoulder height, head turned toward the lens,
     grip visibly tightened — matches the "STOPPED ~4.5-5.5s" beat exactly.
   - 6.5s: hammer lowering, now at chest height.
   - 7.8s: hammer back down at his side.
   Full arc confirmed: hang → rise → stop-at-shoulder → lower → hang.
   **PASS.**
3. **NO plaque, NO mark, NO crack, NO hole anywhere in any frame** —
   confirmed in all six frames: nothing between the lens and Dupe, just the
   empty hall receding behind him. **PASS.**
4. **Camera locked, no cut** — ffmpeg scene-change detection
   (`select='gt(scene,0.10)'`) found **zero** cuts anywhere in the clip.
   **PASS.**
5. **NO words (whisper transcript empty); room tone + breath only, no
   music** — first pass (no VAD) returned one spurious 2-second segment
   reading "You"; re-run with `vad_filter=True` (voice-activity detection)
   returned **zero** segments, confirming the first pass was a
   known faster-whisper hallucination on near-silent/room-tone audio, not
   real speech. **PASS.**
6. **Uniform: white with orange trim, gold V, cap on, curled moustache** —
   confirmed in every frame. **PASS.**

**Overall: S18 take 1 reads as a clean pass on every REVIEW ORDER item, no
deviations to flag.**

## One more observation — S15e-B2 take 2 (recorded, not acted on)

Searched the grid DOM for the known asset id
(`29469056-6b52-4388-9609-86c693219639`, from an earlier operator's report)
— **0 matches**, card not present. Per `docs/reports/absence-s2rf-t1-winbox.md`
(task-1439c7af, ~13:19 ICT 2026-09-09), that exact card was already cancelled
in a prior session: it sat `queued` past 90 minutes, was cancelled via its
own Cancel + in-app Confirm, confirmed absent on two independent reloads, and
Usage History showed a Refunded entry with no charge. No later ledger entry
mentions it being re-fired. Consistent with what I see now (absent from the
grid). Did not touch anything — recording only, per the brief.

## Scene 3 — S2X "THE CRACK" insert

- Sheet: `docs/prompts/absence/s2x-fix1-the-crack-insert.txt`. Lint clean.
  `--chips` expected 1: `loc_hall_big_d` (same hall Element as S15e-AB).
- Staged during S18's render (same composer tab, text/duration edits only):
  cleared, pasted via OS-clipboard `Ctrl+V`, End→space→Backspace. Chip
  count **1/1 bound, 0 error chips** — matches lint exactly. Duration
  changed 8s → 5s via the ARIA slider (`ArrowLeft` × 3, verified
  `aria-valuenow="5"`).
- Once the slot was confirmed free again (S18 card read "Last downloaded",
  no Processing/Generating anywhere), returned to the composer: this time
  the tab had **not** been reloaded since S18 fired, so Unlimited was still
  `true` and needed no re-toggling — confirmed anyway via DOM + full
  screenshot: `UNLIMITED · ~~50~~ · 0`, Seedance 2.5 / 16:9 / 720p / 5s /
  1/4 / High / Sound On, 1/1 chip intact, `innerWidth` 1920.
- **Fired 2026-09-10 03:04:21 ICT (2026-09-09 20:04:21 UTC).** "Generation
  started" toast; asset count 760 → 761; new card entered `Processing`.

### Scene 3 — render wait / harvest

- Polled the separate check tab every ~5min. One `screenshot` "Script
  injection timed out" and one subsequent "0 width" viewport failure on
  that check tab (`window.innerWidth`/`innerHeight` both read `0`) — per
  the HARD rule, checked Usage History first (via a third, throwaway tab):
  most recent entry stayed `Unlimited Seedance 2.5 Spent Sep 10, 2026 3:04
  AM` (the S2X fire itself), no new entry, no charge. The broken tab could
  not be recovered by reload (matches the skill's documented "viewport
  collapsed to 0" failure mode) — closed it and opened a fresh check tab
  per the ladder, rather than resizing or restarting Chrome. The composer
  tab (`1638444803`) was independently confirmed healthy (`1920x911`)
  throughout and never touched by any of this.
- **Finished by ~32 minutes** (fired 03:04:21 ICT, card clear by ~03:35
  ICT).
- Opened the finished card's Info panel
  (`?preview=af78ba26-faa8-4111-a91f-dea400e26b5b`): **Created September
  10, 2026 at 3:04 AM** — matches the fire time exactly. Prompt panel shows
  the exact paste-block opening ("5s · 720p · 16:9 · ONE LOCKED SHOT...").
  Model Seedance 2.5, 720p, High, 1280x720.
- No NSFW flag, no rejection, no rights-verification banner. Downloaded
  cleanly. Downloaded to
  `C:\Users\UsEr\Downloads\hf_20260909_200414_de902248-0c6f-477f-b945-344bd1f6b37a.mp4`
  (3,396,165 bytes). md5 `f128a29a5030f42a5c0858b4b4b29477`. ffprobe:
  1280x720, h264, 24fps, 5.05s duration — exact spec match. Asset count 760
  → 761 at fire time, confirming +1.

#### Review — full resolution, honest, not self-certified

Frames extracted at the sheet's mandated 1, 2.5, 4s into
`docs/reports/frames-s2x-t1/` at full 1280x720 resolution, plus a 640-wide
`contact_row.png` and a 4x zoomed crop of the mark
(`crop_mark_zoom.png`).

**⚠️ Item 0 — THE MARK (the sheet's own hard gate) — likely FLAG, per the
sheet's own explicit criteria. Reporting this plainly, not softening it.**

Ran the exact numeric test the sheet specifies (threshold 80, bbox width
% of frame, fill ratio), on `frame_2.5s.png` (1280x720):

| Test | Result | Gate | Numeric verdict |
|---|---|---|---|
| Absolute threshold 80 (px < 80/255) | 29 px, bbox 15×5px = **1.17%** frame width, fill **0.387** | bbox <8% AND fill ≥0.10 | **numerically passes** |
| Full visible crack extent (rel. darkness vs. 182 wall) | 128 px, bbox 24×38px = **1.88%** frame width | — | small bbox either way |
| Mean darkness of the visible crack's own pixels | **110/255** (wall ≈ 182-215, true black ≈ 0-40) | — | **mid-grey, not black** |
| Darkest single pixel anywhere in the mark | 42/255 | — | a small dark core exists, but is not representative of the whole mark |

**The narrow bbox/fill numbers pass, but the mark visually and by mean
pixel value reads as a thin, PALE GREY/TAN spiderweb crack with a
small textured hole-like core — not the sheet's canon "solid thick
black line... every line solid and heavy like ink and dark for its
whole length."** The zoomed crop (`crop_mark_zoom.png`) shows wispy
hairline branches and a slightly-textured, mottled center that reads
closer to a small hole than to ink. This is close kin to several items
the sheet's own REVIEW ORDER item 0 lists as automatic FLAG conditions:
**"Pale/grey/tan"** and (arguably) **"a hole with edges"** — both listed
disjunctively, independent of the bbox/fill numbers passing.

Why the bbox/fill numbers still pass: threshold 80 only catches the
mark's small darkest core (mean darkness of the full visible crack is
110, well above 80), so the numeric gate — built to catch a
*large/spiderweb-spanning* dark mark — doesn't fire on a mark that's
merely the wrong *colour* rather than the wrong *size*. Flagging this
mismatch explicitly rather than letting the passing numbers stand in for
a verdict.

**Not my call to make — the CTO decides**, per "describe honestly, never
self-certify." Recording the evidence plainly: this reads as a probable
canon-rule-8 violation on colour/character even though the bbox/fill
numbers alone pass.

1. **THE PLAQUE dead centre, the mark above it, ONE mark only** — plaque
   position confirmed dead centre, lower half of frame, across all three
   timestamps (1s/2.5s/4s, frame is static — camera locked). Exactly one
   mark visible anywhere in the frame at any timestamp — no second mark.
   **PASS** on count/position; see item 0 above for the mark's own
   character.
2. **NOBODY in frame, no hand, no shadow of a person, no cart** —
   confirmed in all three frames: empty room, no figures, no shadows, no
   props other than the wall/plaque/columns. **PASS.**
3. **Camera locked, no cut** — ffmpeg scene-change detection
   (`select='gt(scene,0.10)'`) found **zero** cuts anywhere in the 5.05s
   clip; the three sampled frames are visually identical in framing.
   **PASS.**
4. **Room tone only; no music, no words** — VAD-filtered whisper
   transcription (`vad_filter=True`) returned **zero** speech segments.
   **PASS.**

**Overall: S2X take 1 passes items 1/2/3/4 cleanly, but item 0 — the
mark's own canon compliance — reads as a likely FLAG on colour/character
(pale grey/tan spiderweb + hole-like core) even though its bbox/fill
numbers pass the literal gate. Filing as-is per "file the take whatever
the verdict" — the CTO makes the final call.**

## Files changed

- `docs/reports/absence-ab-s18-s2x-t1-winbox.md` (this file)
- `docs/reports/frames-s15e-ab-t1/` (8 full-res frames + contact row)
- `docs/reports/frames-s18-t1/` (6 full-res frames + contact row)
- `docs/reports/frames-s2x-t1/` (3 full-res frames + contact row + zoomed
  mark crop)
- No sheets, no AB-LEDGER.md, no other project files touched.

## Tests run

- `python scripts/prompt-lint.py <sheet>` — clean on all three sheets,
  before touching the browser.
- `python scripts/prompt-lint.py --chips <sheet>` — chip count cross-checked
  against the live composer for all three scenes, exact match every time
  (5/5, 2/2, 1/1).
- ffmpeg scene-change detection (`select='gt(scene,N)'`) on all three
  downloaded clips, to verify cut count/timing.
- faster-whisper transcription (VAD-filtered where silence was expected) on
  all three clips, to verify spoken-line content/order or confirm silence.
- Pixel-level canon-rule-8 measurement (threshold/bbox/fill + mean
  darkness) on S2X's wall-mark frame.
- md5 + ffprobe on all three downloaded files, matched against the fire
  timestamp and the sheet's spec (duration/resolution).

## Blockers

None — all three scenes fired, rendered, downloaded and reviewed. Two
transient `zoom` CDP timeouts and one tab viewport-collapse (0x0) during
status polling, all recovered per the skill's documented ladders (Usage
History check, then fresh tab), never touching the staged composer, no
charge landed at any point (confirmed via Usage History repeatedly — every
entry across the whole session reads `Unlimited ... Spent`, $0).

**One item that is not a blocker but needs the CTO's judgment**: S2X's
wall mark likely fails canon rule 8 on colour/character (see Scene 3
review above) even though the take is otherwise clean. Did not re-fire —
per the brief, "file the take whatever the verdict."

**One self-corrected process error**: mid-Scene-1-wait, I navigated the
staged S18 composer tab directly for a status check instead of using a
separate tab (see Scene 1 render-wait notes). No money impact — the draft
survived and Unlimited was simply re-verified/re-enabled before firing,
per the money rules. Flagging so the next operator's brief can reinforce
"status checks always go through a separate tab, never the staged
composer."
