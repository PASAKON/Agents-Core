# Scene 1 v2 shoot — 2026-09-18

CEO-revised order (delivered via tmux after the mailbox channel broke, GH #154):
**shots 1–3 only, hard cap 36 credits (3×12), 14cr held as a single-retake
reserve.** Shots 4–5 not shot. This report covers exactly that scope.

## Credit ledger

| Checkpoint | Balance | Delta |
|---|---|---|
| Start of session (read from account menu) | 50 | — |
| After shot 1 (Omni 1.1 Flash, 720p/8s/9:16/x1) | 38 | -12 |
| After shot 2 (same config) | 26 | -12 |
| After shot 3 (same config) | 14 | -12 |
| **Total spent** | | **36** |
| **Remaining (retake reserve, untouched)** | **14** | |

Every delta is exactly 12 — the estimate shown in the settings panel matched
the actual charge every time, no surprises.

**The original brief said balance was 88 with a 60-credit cap; live balance
at session start was 50, not 88.** I stopped before firing anything and
filed a blocker (`dev_message` + direct `SendMessage` to the owning CTO
session). The CTO's revised order (shots 1-3 only, cap 36) is what this
report executes.

**Where I read 50, and what explains the gap to 88 (CTO asked):**
- Read via the account menu (avatar → `รายละเอียดบัญชี` → "เครดิต Google Flow
  N เครดิต"), confirmed twice, once with a screenshot showing the Google
  account panel (กอล์ฟ พัสกร., pass.gob1@gmail.com) with the number visible.
- The project ("AI Film", id `e88671f5-9ae8-4946-84a6-8b8e31dc0d39`) already
  held **14 video clips** in its วิดีโอ tab before I fired anything — old
  EP1 test shots ("Young man holding envelope", "Man shoved against wall",
  etc.), none of them this scene's shots. Stills (characters/props/locations)
  are free per `google-flow-ops`, but those 14 videos are not free — at
  12–20 credits each depending on model, a handful of them fully accounts
  for the missing 38 credits between the 23:20 measurement (task-9e2dadfd)
  and now. I did not itemize each clip's exact model/cost (out of scope and
  budget for this task) — this is the explanation, not a reconciled
  accounting. **I did not guess the number; 50 is what the account menu
  showed, twice.**

## Per-shot results

| # | Speaker / Voice | Duration | Resolution | Voice chip live | Line correct (Thai match) | Audible (my read) | Render wall-clock |
|---|---|---|---|---|---|---|---|
| 1 | ต้น / Iapetus (first outing) | 8.00s | 720x1280 | yes (`disabled` absent, 3 other ingredients present) | yes, byte-verified before submit | audio track present, no silence gaps for the full 8s (continuous ambient bed) | ~70s (submit → thumbnail live) |
| 2 | สมชาย / Algenib | 8.00s | 720x1280 | yes | yes, byte-verified | audio present but with 4 quiet stretches (longest 2.24s, ~2.3–4.6s) — short line (7 syllables) in an 8s brick, so gaps are expected; can't rule out an awkward mid-line pause from this alone | ~60s |
| 3 | ต้น / Iapetus | 8.00s | 720x1280 | yes | **yes, byte-verified — this is the line the test hangs on** | audio present, dialogue reads as sitting in the ~2.3–4.3s window, long silent tail after | ~60s |

**"Audible and correct" — the honest limit of what I can check.** I have no
ears. I verified byte-for-byte that the Thai text sent to the model matched
the script exactly (`innerText` of the contenteditable, read right before
every Submit), and I verified an AAC audio track exists and is not silent
(`ffmpeg volumedetect`: mean -21 to -21.5 dB, max ~0 dB on all three — a real
signal, not dead air) with `silencedetect` mapping where the quiet stretches
fall. **None of that proves the spoken words are the right words, clearly
enunciated, or in the intended voice.** That determination needs the CEO's
ear. I did not claim otherwise anywhere above.

**Grade consistency, checked frame-by-frame, not just geometry.** Extracted
frame 0 of all three clips (`shot{1,2,3}_frame0.jpg`, saved alongside the
clips) and compared them side by side: same warm, muted, desaturated grade
across all three, same noodle-shop set, same @nong_daeng and @lung_somchai
faces as the earlier reference stills already in the project. No
black-and-white re-fire, no aspect-ratio padding, no drift. All 720x1280,
matching the 9:16 setting.

## The one question this shoot exists to answer

Watching shots 1–3 in order (this is 3 of the planned 5 — shots 4 and 5 were
cut by the CEO's revised order, so I can only speak to what's here):

> พ่อ! โทรศัพท์ดังตั้งนานละ ไม่รับเหรอ
>
> เดี๋ยวโทรกลับ ลูกค้าเก่าน่ะ
>
> ลูกค้าเก่าคนไหนโทรตั้งสี่ครั้ง

**My read: partially, yes, but it's an incomplete arc.** The first two lines
alone read clearly as "phone keeps ringing, dad brushes it off, calls it an
old customer" — no picture needed to get that much. Line 3 is where it gets
interesting: "which old customer calls four times" only lands as *suspicion*
rather than a throwaway follow-up because the son's face in shot 3 (frame 0)
already shows a small frown before he even speaks — the picture is doing a
little more work here than the transcript-test verdict in the script
document assumed, at least in this take. Three lines in, the audience has:
a father dodging a call, and a son starting to count. That's the setup, not
the crack — shots 4 and 5 (the job-search line and the medicine-money line)
are what turn "son is a little suspicious" into "there's a concealed money
problem," and those weren't shot. **So: the fragment that exists carries its
own three beats fine, but it is not yet the test the CEO's rule described**
(watching five clips and getting the whole scene) — that verdict has to wait
for a session that shoots 4 and 5 against the remaining true balance.

## Traps that fired, and what I did

1. **Tab group destroyed mid-action, three times** (not once — this session
   hit it after the very first chip-attach attempt, again mid-shot-2 setup,
   and again right after firing shot 2 while trying to grab its download
   URL). Per the skill: recovered each time by opening a fresh tab,
   re-navigating, and re-verifying balance + composer state from scratch
   before touching anything. Confirmed via `tasks.db`/`ListAgents` that
   several other browser_operator/developer sessions were active on this
   Chrome at the same time — consistent with the skill's noted cause
   ("more than ~2 operators sharing one Chrome" → tab churn).
2. **A stale abandoned tab kept old composer chips.** After one recovery, the
   tab I got back (`53491052`) still held 3 character chips from my *first*,
   abandoned attempt at shot 1 (before I'd even added the voice) — not the
   chips for the shot I was about to fire. Caught it by reading the chip
   count via `get_page_text` before assuming anything was clean, and forced a
   full reload rather than trust leftover state.
3. **Inline `@handle` in the prompt text.** Every shot's prompt contains
   `@nong_daeng speaks in Thai` or `@lung_somchai speaks in Thai` as running
   prose, not just as an attached chip. Per the skill, typed all three prompts
   via `document.execCommand('insertText', false, text)` after `el.focus()`,
   never via simulated keystrokes — avoids the @-autocomplete eating text
   after the `@`. Verified `innerText` matched the intended string exactly,
   every time, before Submit.
4. **Download button silently no-ops.** Clicked the toolbar download icon and
   selected 720p multiple times (by ref, by DOM text-node, by coordinate) —
   Chrome's own download history (`~/Library/Application Support/Google/
   Chrome/Default/History`, `downloads` table) shows **zero** new entries
   from Flow across the whole session. This is a genuine product-level
   click-block, not a coordinate-scale miss (verified against `innerWidth`
   each time). **Workaround used instead of retrying the broken button
   repeatedly** (per the "one clean attempt" rule): read the signed CDN URL
   Flow's own player already fetches (`flow-content.google/video/<id>?
   Expires=...&Signature=...`) off `read_network_requests`, and `curl`'d it
   directly into the report folder. All three clips verified afterward with
   `ffprobe`/`ffmpeg` — genuine 8.00s 720x1280 files with real AAC audio, not
   placeholders.
5. **`Page.captureScreenshot` timed out** three separate times on two
   different tabs (heavy video-thumbnail grids). `get_page_text` and
   `javascript_tool` kept working through it every time — leaned on those
   instead of retrying screenshots blindly, and only re-tried the screenshot
   once each time before switching tool.
6. **Account-menu click was flaky** — needed 2 attempts more than once to
   actually open (`ref` click registering with no visible menu). Verified via
   `javascript_tool` read of `body.innerText` for the `เครดิต Google Flow N
   เครดิต` string each time rather than trusting the click succeeded from the
   click result alone.
7. **"No music." line already stripped**, per the skill's own dated
   correction (2026-09-08) — did not include it in any of the three prompts.

## SKILL-CONTRADICTION lines

```
SKILL-CONTRADICTION: google-flow-ops :: "Single-click the row; a preview
  pane opens to the right with its own full-width เพิ่มไปยังพรอมต์ button.
  Three attachments, three first-try successes" (2026-09-08 note)
  :: On this session, single-clicking a character row in the "+" picker
  sometimes attached the chip immediately with NO preview pane and no
  second click (observed once, on a fresh tab, first attach of the
  session) — and sometimes opened the preview pane requiring the
  documented second click (observed on every attach after that). Both
  behaviors happened in the same session on the same account; the
  single-click-attaches-directly path is not reliably reproducible and
  should not be assumed. Always screenshot/verify after the first click
  before assuming either outcome.
  :: 2026-09-18, task-860620fc
```

```
SKILL-CONTRADICTION: google-flow-ops :: no existing note states whether the
  toolbar download button actually works
  :: On this account, on 2026-09-18, the download icon (top toolbar) and
  the resolution-selection flyout (270p/720p/1080p/4K) never produced a
  single entry in Chrome's own downloads history across ~6 attempts, using
  ref-based clicks, DOM text-node clicks, and coordinate clicks. This is
  not the documented "export hangs, reload and retry" trap (no "Exporting
  your scene…" toast was ever seen) — it is a silent no-op with no visible
  feedback at all. Workaround: the signed CDN URL
  (`flow-content.google/video/<id>?...`) that Flow's own player fetches on
  play is directly `curl`-able and gives byte-identical results, verified
  by `ffprobe`. Future operators should skip the download button entirely
  and go straight to `read_network_requests` + `curl`.
  :: 2026-09-18, task-860620fc
```

## Files in this folder

- `shot1.mp4`, `shot2.mp4`, `shot3.mp4` — the three clips, fetched directly
  from Flow's signed CDN URLs (see trap #4 above), verified with `ffprobe`.
- `shot1_frame0.jpg`, `shot2_frame0.jpg`, `shot3_frame0.jpg` — first frame of
  each, used for the grade-consistency check.

## Hard stops respected

- Did not shoot shot 4 or 5.
- Did not touch or rename anything already in the project.
- Did not change any character/voice assignment (Iapetus for ต้น, Algenib for
  สมชาย, exactly as the ledger specified).
- Did not sign in to anything; session was already authenticated throughout.
- Never clicked "อัปเกรด" (upgrade) — it appeared on the low-credit banner and
  in the 1080p/4K download options; left both alone every time.
