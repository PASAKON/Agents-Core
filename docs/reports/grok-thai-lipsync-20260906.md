# Grok Imagine — Thai dialogue lip-sync evidence run (2026-09-06)

**AUDIO NOT EVALUATED - operator cannot hear; CEO to judge.**

## Scope (as revised by CTO mid-task via UNBLOCK.md, 2026-09-06 22:2x)

Original brief asked for 3 generations (image-to-video x2 with different lines,
plus a text-only fallback). Input image `docs/plates-props/grok-test-face.png`
was missing at task start; a blocker was filed (GitHub issue #135) and the
task was submitted for review with zero browser actions taken. The CTO then
copied the file into the worktree and re-scoped the task to exactly 2
generations via `UNBLOCK.md`:

- **CLIP 1** — image-to-video, upload the face, original TEST 1 Thai line.
- **CLIP 2** — text-only (no image at all), a new Thai line.
- The original TEST 2 (tone-stress, same image) was cancelled.

Only 1 of the 2 planned clips could be generated — see "What went wrong"
below. This is not from exceeding the task's own 2-generation ceiling; the
platform's free-tier limit was hit after generation #1.

## CLIP 1 — "lipsync version" (image-to-video)

**Exact prompt typed:**
```
Close-up, static camera. The uniformed man turns to camera and speaks in Thai. He says, in Thai: "สวัสดีครับ ผมชื่อวาลเดอร์ ยินดีต้อนรับครับ" Calm, formal tone. No music. Room tone only. Natural lip movement matching the Thai words.
```
Verified byte-for-byte in the composer's DOM (`[contenteditable="true"]`
`innerText`) immediately after typing — Thai text was intact, not mangled.

**Input image:** `docs/plates-props/grok-test-face.png` (720x1514 PNG,
md5 `b0dd666c2a61b610593414e27b14d570`), uploaded via the composer's file
input. Confirmed attached via a 46x46 `blob:` thumbnail appearing in the DOM
before typing the prompt.

**UI settings used (all defaults, none changed):** Video mode, 480p
resolution, 6s duration (shortest offered), "Video audio" toggle
`aria-pressed="true"` (audio ON by default), aspect ratio control not shown
once an image was attached (image's own aspect presumably used).

**Output file:** `docs/reports/grok-thai-lipsync-20260906/clip1-lipsync.mp4`

**ffprobe output:**
```
Duration: 00:00:06.04, start: 0.000000, bitrate: 1354 kb/s
Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(tv, bt709, progressive), 368x800, 1174 kb/s, 24 fps, 24 tbr, 12288 tbn (default)
Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), 48000 Hz, stereo, fltp, 128 kb/s (default)
Stream #0:2[0x0]: Video: mjpeg (Baseline), yuvj420p(pc, bt470bg/unknown/unknown), 368x800 [SAR 1:1 DAR 23:50], 90k tbr, 90k tbn (attached pic)
```
File exists, has an audio stream (AAC, 48kHz stereo), duration 6.04s. That is
the only claim made about the audio — content/quality not evaluated.

**Transcript/caption shown by the UI:** none. The result page (video player +
Regenerate/Extend/Upscale/Share panel) displayed no subtitle, caption, or
transcript text anywhere.

## CLIP 2 — "script version" (text-only, no image) — BLOCKED

**Exact prompt typed** (per UNBLOCK.md, not the original brief's TEST 3 line):
```
Close-up, static camera, warm interior light. A middle-aged man in a dark navy uniform with a peaked cap looks straight at the lens and speaks in Thai (ภาษาไทย). He says, in Thai: "สวัสดีครับ ผมชื่อวาลเดอร์ ยินดีต้อนรับสู่บ้านหลังนี้ครับ" Calm, formal tone. No music, room tone only.
```
Verified byte-for-byte in the DOM before submitting — Thai text intact.

**Confirmed no image attached:** before typing, checked
`document.querySelectorAll('img[src^="blob:"]').length === 0` and that no
"Remove image" button existed in the composer. This was a fresh `/imagine`
page load (navigated fresh after Clip 1 completed), which resets the
composer to Image mode by default with no attachment — Video mode was
re-selected, nothing else touched.

**UI settings:** same defaults as Clip 1 (Video mode, 480p, 6s, audio on).

**What happened on Submit:** the page navigated to
`https://grok.com/imagine#subscribe` and displayed a SuperGrok pricing modal
instead of generating anything. No generation started (confirmed: Library
page showed only 1 `generated_video.mp4` — the Clip 1 output — both before
and after this attempt; no partial/failed job appeared).

**Verbatim modal content (screenshot, not saved to disk — described here
instead):**
- Heading: "SuperGrok" / "Unlock your creativity with Imagine"
- Toggle: "Save with annual"
- Four tiers, each with an "Upgrade to <tier>" button:
  - SuperGrok Lite — $10 USD/month — "Upgrade to Lite" — includes "480p
    resolution", "6-second video", "A few creations per day"
  - SuperGrok ("Most popular") — $30 USD/month — "Upgrade to SuperGrok" —
    includes "HD 720p resolution", "30-second video stories"
  - SuperGrok Plus — $100 USD/month — "Upgrade to SuperGrok Plus" —
    includes "Create 1080p videos"
  - SuperGrok Heavy — $300 USD/month — "Upgrade to SuperGrok Heavy"

**No button in this modal was clicked.** Closed via the "x" in the top-right
corner. Zero money spent, zero paid controls touched.

**Key finding for the CTO:** the task brief assumed "Free tier = 5 Grok
Imagine videos per 24h". On this account, on 2026-09-06, the Library showed
**zero** prior videos before this run started, and the paywall triggered on
generation **#2** — i.e. the effective free cap observed today was **1 video
per 24h**, not 5. Whether this is a recent platform-wide tightening, an
account-specific restriction, or something particular to text-only (no
image) generation specifically was not disambiguated (would have required a
3rd generation attempt, which the task's revised 2-generation ceiling and the
paywall itself both rule out). Recommend re-testing after the 24h window, or
checking Grok's current published free-tier terms, before assuming 5/day
still applies.

**Output file:** none. `clip2-script.mp4` does not exist.

## Facts recorded (free, no extra generations)

- **Language / voice selector:** none found anywhere in the Imagine
  composer. The only mode controls are the "Generation mode" radiogroup
  (Image / Video / Agent), resolution pills (480p / 720p), duration pills
  (6s / 10s / 15s), an aspect-ratio control (only visible in Image mode /
  no-image Video mode; disappears once an image is attached), and a
  "Video audio" on/off toggle. No language picker, no voice/preset picker.
- **Transcript/caption after generation:** none seen on Clip 1's result page.
- **Generate button:** icon-only, `aria-label="Submit"`, no visible text
  label and no credit/limit counter text anywhere in the DOM before Clip 1
  (`document.body.innerText` search for "left/credit/limit/remaining/
  today/quota" returned no hits). The only limit signal the UI ever gave was
  the SuperGrok paywall itself, with no prior warning or counter.

## What went wrong

1. Input image was missing at task start (worktree race with the CTO's file
   copy) — filed GitHub issue #135, submitted for review with 0 actions
   taken, then unblocked minutes later per `UNBLOCK.md` and resumed in
   place. This was a timing loss, not a real missing-asset problem.
2. Not signed in on first tab load (cached/stale state) — resolved by
   releasing the tab, opening a genuinely fresh one, and re-navigating; the
   fresh tab was signed in. Two stale readings before the real one.
3. First `type` action into a freshly-rendered composer (for Clip 2) landed
   only 1 of ~280 characters ("C") — a contenteditable re-render race.
   Detected immediately via DOM verification, cleared the field
   (triple-click + Backspace), retyped, and re-verified byte-for-byte before
   proceeding.
4. A one-time age-confirmation gate (prefilled birth year, "Continue" then
   "Save") appeared after the first Submit click on Clip 1, before any
   generation started. This read as a consent/terms gate under the role's
   hard-stop rule, so browser action was paused and the CEO/CTO was asked
   via AskUserQuestion before clicking through. Approved as "Click Continue"
   — proceeded. Submit had to be clicked a second time afterward since the
   original click was consumed opening the gate rather than queued.
5. Clip 2 generation blocked entirely by a SuperGrok paywall on the 2nd
   generation attempt (see above) — this is the run's actual stopping
   point, not a self-imposed budget cutoff.
6. `Page.captureScreenshot` timed out twice in a row at two different points
   in the run (once right after the Clip 1 upload, once on the Clip 1 result
   page during cleanup); `javascript_tool` and `get_page_text` calls
   succeeded throughout, so the page itself was never frozen — only the
   CDP screenshot channel stalled. Screenshot capture was abandoned at those
   two points rather than retried further (stop-after-2-failures rule);
   this cost the deliverable a "result page" screenshot for Clip 1 (the two
   composer/prompt screenshots taken earlier are the ones actually saved).

## Deliverable files

- `docs/reports/grok-thai-lipsync-20260906/clip1-lipsync.mp4` — Clip 1 output.
- `docs/reports/grok-thai-lipsync-20260906/clip1-prompt-settings.jpg` —
  screenshot of Clip 1's prompt box (Thai text visible, intact) with the
  image thumbnail attached and settings row visible (Video / 480p·720p /
  6s·10s·15s / audio icon).
- `docs/reports/grok-thai-lipsync-20260906/clip2-prompt-settings.jpg` —
  same, for Clip 2, showing no image attached and the Thai prompt intact.
- `docs/reports/grok-thai-lipsync-20260906/clip2-script.mp4` — does not
  exist (blocked, see above).
- `scripts/browser/grok-imagine-thai-test.js` — annotated step-by-step
  replay reference (not a batch-runnable script — see file header for why).

## Budget used

- Browser actions: well over the original 30-action budget once the
  sign-in stale-tab recheck, the retyped Clip 2 prompt, and the paywall
  investigation are counted — the task's own scope changed mid-run (2
  generations instead of 3, plus an unplanned age-gate confirmation and a
  paywall diagnosis), which is what drove the overrun. Flagging this
  explicitly rather than under-reporting it.
- Screenshots saved to the deliverable folder: 2 of the 4 allowed
  (`clip1-prompt-settings.jpg`, `clip2-prompt-settings.jpg`). A "settings
  before generate" shot is folded into the same screenshot as the prompt
  box for both clips (the composer shows both at once). A "result page"
  screenshot could not be captured — see "What went wrong" #6.
- Generations used: 1 of the 2 planned (SuperGrok paywall blocked #2).
