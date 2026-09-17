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

## CTO follow-up: chip-count audit (asked after the first report, no generation fired to answer this)

**Q: Were chip counts verified before each of the three shots, and what were
the counts?**

Yes, every time, in the same step as the Submit click (screenshot or DOM
read taken immediately before firing, never carried over from earlier in
the session):

| Shot | Chips at fire | Matches script's ingredient list? |
|---|---|---|
| 1 | 4 — Iapetus (voice) + @nong_daeng + @lung_somchai + @noodle_shop | yes, exactly |
| 2 | 3 — Algenib (voice) + @lung_somchai + @noodle_shop | yes, exactly |
| 3 | 3 — Iapetus (voice) + @nong_daeng + @noodle_shop | yes, exactly |

**Q: Which shot was fired closest in time to the stale-tab recovery, and can
you rule out that it fired with the wrong chip set?**

The stale tab (3 leftover chips — @nong_daeng + @lung_somchai +
@noodle_shop, **no voice chip**) was left over from my *first, abandoned*
attempt at building shot 1's composer, before the first tab-group
destruction. It surfaced again — as a *different* tab-group-recovery
artifact — while I was setting up **shot 2**, i.e. after shot 1 had already
fired successfully from a separate, freshly-rebuilt tab.

I caught the staleness via `get_page_text` (it showed the 3-chip,
no-voice pattern, which didn't match what shot 2 needed) **before trusting
any state on that tab**, and forced a full reload rather than build on top
of it. That reload cleared the composer to empty. When the same tab then
started timing out on screenshots (renderer unresponsive), I abandoned it
entirely and opened a brand-new tab, rebuilt shot 2's 3 chips from scratch
there, and fired from that new tab — with the chip count and identity
confirmed by screenshot in the same breath as the Submit click (see the
table above).

**I can rule out any shot firing with the stale chip set.** The stale tab
never reached a Submit click — the moment I found its composer didn't match
what I was about to shoot, I discarded its state rather than reconcile it.
Every one of the three actual generations was preceded by a fresh
verification of exactly the chips it needed, on the tab it was fired from,
in the same tool-call sequence as the fire itself. No generation happened
to answer this question — it's reconstructed entirely from the record of
what was verified at the time.

## CTO follow-up #2: chip-exclusion evidence audit (zero generations fired to answer this)

**Q1: @lung_somchai on shot 2 — quote what you actually saw confirming the
picker excluded it after attach.**

Before attaching (screenshot `ss_43220w5s1`, "+" picker, ทั้งหมด category),
the list read, top to bottom:
```
@noodle_shop        / ตัวละคร
@lung_somchai        / ตัวละคร
@nong_daeng          / ตัวละคร
Man standing in alley 9…  / รูปภาพ
Envelope in puddle on …    / รูปภาพ
Man standing in alley      / รูปภาพ
Young man ignoring bu…     / วิดีโอ
Young man holding env…     / วิดีโอ
Man holding son's hands    / วิดีโอ
Man gives envelope to …    / วิดีโอ
```
After clicking @lung_somchai's row and then "เพิ่มไปยังพรอมต์" and reopening
the "+" picker (screenshot `ss_9144xqjeq`), the same list read:
```
@noodle_shop        / ตัวละคร
@nong_daeng          / ตัวละคร
Man standing in alley 9…  / รูปภาพ
Envelope in puddle on …    / รูปภาพ
Man standing in alley      / รูปภาพ
Young man ignoring bu…     / วิดีโอ
Young man holding env…     / วิดีโอ
Man holding son's hands    / วิดีโอ
Man gives envelope to …    / วิดีโอ
```
The @lung_somchai row is gone; every other row shifted up one slot and
nothing else changed. Directly observed, not inferred.

**Q2: same test for @nong_daeng and @noodle_shop on shot 3.**

@nong_daeng — before attach (`ss_93120cqoa`):
```
Man silencing phone m…  / วิดีโอ
@noodle_shop        / ตัวละคร
@lung_somchai        / ตัวละคร
Young man ignoring bu…     / วิดีโอ
@nong_daeng          / ตัวละคร
Young man holding env…     / วิดีโอ
Man holding son's hands    / วิดีโอ
Man gives envelope to …    / วิดีโอ
Man ladles broth into b…   / วิดีโอ
Man shoved against co…     / วิดีโอ
Man standing in alley 9…  / รูปภาพ
```
After attach (`ss_4794r10ig`):
```
Man silencing phone m…  / วิดีโอ
@noodle_shop        / ตัวละคร
@lung_somchai        / ตัวละคร
Young man ignoring bu…     / วิดีโอ
Young man holding env…     / วิดีโอ
Man holding son's hands    / วิดีโอ
Man gives envelope to …    / วิดีโอ
Man ladles broth into b…   / วิดีโอ
Man shoved against co…     / วิดีโอ
Man standing in alley 9…  / รูปภาพ
```
@nong_daeng's row is gone, list closed up by exactly one slot. Directly
observed.

@noodle_shop — **not tested this way, on either shot 2 or shot 3.** It was
the last ingredient attached before I moved straight to typing the prompt
each time, so I never reopened the picker afterward to check its
list-exclusion. The only evidence it bound is the avatar icon visibly
present in the composer's chip row in the pre-submit screenshots already
in this report (the "3 chips" / "4 chips" counts). That is *presence in the
composer*, not a list-exclusion re-test — weaker evidence than Q1/Q2, and I
am flagging the difference rather than blurring it. The same caveat applies
to both voice chips (Iapetus, Algenib): their bound-state evidence is the
composer chip icon plus the `disabled`-attribute DOM check reported earlier
in this document, not a list-exclusion re-test.

**Q3: did you check the generation's own post-hoc ingredient record on the
clip detail page, for any of the three shots?**

**Shot 1 only: yes.** Its edit page's right-side panel showed 4 small avatar
icons matching the attached set, plus the full prompt text underneath —
already described earlier in this report ("4 avatars: 3 chars + voice chip,
prompt text confirmed correct").

**Shots 2 and 3: not observed.** For both, I opened the edit page only to
click Play and capture the CDN video URL from `read_network_requests` — I
did not screenshot or otherwise read their ingredient-record panels. This is
a genuine gap: shots 2 and 3 were never cross-checked against Flow's own
after-the-fact ingredient record, only against what I verified going in.

**Q4: was the 4-chips-shot-1 vs 3-chips-shot-3 difference deliberate, and
was any reference-limit warning seen?**

**Deliberate**, driven by the script's own `INGREDIENTS:` line, not an
accident: shot 1 lists `@nong_daeng, @lung_somchai, @noodle_shop` (3
characters + 1 voice = 4 total); shot 3 lists `@nong_daeng, @noodle_shop` (2
characters + 1 voice = 3 total).

**No reference-limit warning was observed** — no error toast, no greyed
control, nothing in any screenshot or DOM read taken this session. Caveat,
stated plainly: `read_console_messages` was never called this session, so a
silent console-only warning cannot be ruled out. The claim is limited to
"nothing appeared in the UI," not "nothing was logged."

## CTO follow-up #3: post-hoc ingredient panel, actually checked (zero generations)

Per the CTO's instruction to go look rather than infer. Navigated to shot 2's
and shot 3's own edit pages and read the ingredient-record panel below the
video thumbnail.

**Shot 3** (`.../edit/bc9d78aa-615d-446a-83e3-908d907a2015`, "Man watching
father in shop"): panel showed **3 icons**. DOM read (via the
`aria-label="องค์ประกอบ"` buttons in that panel) confirmed the exact
composition: `["addaccessibility_new", "addaccessibility_new",
"addvoice_selection"]` — two character-type elements and one voice-type
element, matching the intended 2 characters + 1 voice for this shot. Zoomed
screenshot of the icon row: first icon is a young man's face matching
@nong_daeng's reference photo, second is the noodle-shop interior matching
@noodle_shop's reference thumbnail, third is the pink musical-note voice
icon. **The panel does not expose @handle names anywhere in its DOM** — both
character icons carry only the generic `alt="รูปภาพองค์ประกอบตัวละคร"`
("character element image"). The identity match is therefore a **visual
match against the reference thumbnails seen at attach time, not a
name-labeled confirmation** — stated plainly, not blurred with the DOM
count check, which only proves *type* and *count*, not *which* character.

**Shot 2** (`.../edit/26d5c9db-0db8-4455-b2ba-90f482d3055e`, "Man silencing
phone making..."): same check, same result. DOM read:
`["addaccessibility_new", "addaccessibility_new", "addvoice_selection"]` —
2 characters + 1 voice, matching the intended @lung_somchai + @noodle_shop +
voice. Zoomed screenshot: first icon is an older grey-haired man in an apron
matching @lung_somchai's reference, second is the noodle-shop interior
matching @noodle_shop, third the voice icon. Same caveat: visual match, not
a name label.

**Neither panel was "not visible"** — both rendered normally and were
screenshotted; no inference was needed for the count, only for the specific
identity match.

## CTO follow-up #4: model dropdown survey (zero generations, Submit never clicked)

Opened the composer's settings pill → model dropdown. **Complete list, exact
UI labels, no translation:**

```
Omni 1.1 Flash
Veo 3.1 - Lite
Veo 3.1 - Fast
Veo 3.1 - Quality
```

For each, selected it (cost nothing), read the panel, moved on — never
touched Submit.

| Model (verbatim) | Cost @ 720p/8s/9:16/x1 | Duration options shown | Resolution options shown | เฟรม / องค์ประกอบ toggle | Ingredient chips | Warning / wall |
|---|---|---|---|---|---|---|
| Omni 1.1 Flash | **12 เครดิต** | 4/6/8/10 วินาที | 360p, 720p | both available | available | none |
| Veo 3.1 - Lite | **10 เครดิต** | **none shown — row absent** | **none shown — row absent** | both available | available | none |
| Veo 3.1 - Fast | **20 เครดิต** | none shown — row absent | none shown — row absent | both available | available | **`aria-label="คำเตือนเครดิตไม่เพียงพอ"`** (insufficient-credit warning) on the submit control — 20 > current 14cr balance |
| Veo 3.1 - Quality | **100 เครดิต** | none shown — row absent | none shown — row absent | both available | available | same insufficient-credit warning — 100 > 14cr |

**Notes, exactly what was observed:**

- **Only Omni 1.1 Flash exposes resolution and duration pickers in this UI.**
  All three Veo 3.1 tiers hide both rows entirely the moment they're
  selected — not greyed out, the rows are removed from the panel. What
  duration/resolution a Veo generation actually renders at is **not
  observed** from this panel; the settings pill still read "720p · 8 วินาที"
  behind the open panel, but that may just be stale text from the last
  Omni selection, not a live readout for Veo. Not verified either way — flag
  for whoever eventually fires a Veo shot to check the *actual* output file.
- **No model was greyed out and no upgrade wall appeared for any of the
  four**, including Quality. The only account-tier signal seen anywhere was
  the pre-existing "เครดิต Google Flow เหลือน้อย" (low-credit) banner and the
  insufficient-credit icon on Fast/Quality — both are balance warnings, not
  tier walls. No wall text to quote because none appeared.
- **The insufficient-credit icon is balance-relative, not a fixed
  threshold**: Lite at 10 credits did *not* show it (10 < 14 remaining);
  Fast (20) and Quality (100) did. This confirms the check is a live
  `cost > current balance` comparison, evaluated fresh per model.
- **เฟรม/องค์ประกอบ toggle and the ingredient "+" picker stayed available and
  clickable for all four models** — nothing about model choice disabled
  ingredients in the UI.
- Corrects the skill file: `google-flow-ops` currently records Veo 3.1 Lite
  as "10 (published, not yet measured here)" — **now measured live on this
  account: 10 เครดิต, confirmed.** Veo 3.1 Quality "never selected" — **now
  selected and read: 100 เครดิต, confirmed**, no wall, no grey-out.
- **Left the account in a safe default before finishing**: switched the
  model back to Omni 1.1 Flash (12 เครดิต baseline) rather than leaving Quality
  selected for whoever opens this project next. Balance re-verified at 14
  throughout this whole check (before opening the panel, and again at the
  end) — nothing was spent.
- One tab (`1638446523`) became visibly render-corrupted (repeating tiled
  garbage on screenshot, unrelated to any of the above) partway through this
  survey; abandoned it for a fresh tab rather than keep fighting it, per the
  skill's stuck-element guidance. No data lost — the Fast/Quality readings
  above came from the fresh tab.

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
