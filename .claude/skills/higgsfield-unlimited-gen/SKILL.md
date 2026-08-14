---
name: higgsfield-unlimited-gen
description: Domain-specific safety rules and operating patterns for driving Higgsfield.ai (Seedance/AI video generation) in Unlimited Mode, where real credits must never be spent by accident. Trigger on /higgsfield-unlimited-gen and proactively whenever a C-level is about to delegate or drive browser work on higgsfield.ai, or when the request mentions "Higgsfield", "Seedance", "Unlimited mode video gen", "AI video generation credits", "jump-cut pass", or a Higgsfield History/Recreate/Rerun button. Supplements — does not replace — `browser-operator` (generic browser cost-discipline) and `dev-spawn-protocol` (generic DEV spawning): follow both of those plus everything here for any Higgsfield task. Do NOT fire for video generation on other platforms (fal.ai, Kling, Veo) — those have their own cost rules elsewhere.
---

# Higgsfield Unlimited-Mode Generation — Safety Rules

Every rule below was learned from a real incident in this org, not written
speculatively. Follow `browser-operator`'s general discipline (text-first,
zoom over screenshots, replay scripts) and `dev-spawn-protocol`'s spawn steps
first — this skill adds the Higgsfield-specific layer on top.

## What it does

Gives any C-level (CTO, CMO, CFO, CGO) driving or delegating Higgsfield.ai
video generation the exact button-level rules, editor gotchas, and wait
pattern that prevent (a) accidentally spending real credits when the task
must run Unlimited-only, and (b) a spawned DEV silently dying during a long
render wait.

## When to invoke

- Before delegating any `browser_operator` task whose target is
  `higgsfield.ai`.
- Before writing a task brief that mentions Seedance, Unlimited Mode, jump-cut
  generation, or a "Recreate"/"Rerun" History card.
- Before a C-level personally drives Higgsfield in Chrome for any reason.
- When continuing/resuming a multi-wave Higgsfield generation job started in
  a prior session.

## When NOT to invoke

- Video/image generation on any other platform (fal.ai, Kling, Veo, MeiGen,
  Nano Banana) — those aren't Higgsfield and don't share these UI traps.
- Higgsfield work that is explicitly credit-based/paid by design (not this
  org's normal mode) — if a task genuinely intends to spend credits, that's
  an `feedback_ask_before_paid_api` conversation with the CEO, not this skill.

## The incidents this is built from

**Incident 1 — Rerun auto-fire.** A DEV clicked **"Rerun"** on a History
card, intending only to load its references into the composer for editing.
Rerun does two things at once with **zero confirmation step**: loads the
prompt into the composer, AND immediately fires a new generation of the
unmodified original prompt — at whatever pricing is currently showing,
completely independent of the Generate button or the Unlimited Mode toggle.
It cost **130 real credits**, confirmed via Higgsfield's own Usage History
log (Account Settings → Usage): one entry that day read `130 credits ·
Seedance 2.5 · Spent`, every other entry that day read `Unlimited Seedance
2.5 · Spent` ($0). Reference: mooniex-agents task-eed61860, GH issue #45.

**Incident 2 — keystroke-type timeout auto-fired a paid generation with no
click at all.** A DEV entered a long multi-paragraph prompt (with blank
lines between paragraphs) using a keystroke-simulating "type" action instead
of the mandated synthetic-paste technique (see Editor gotchas). The type
call errored out (`CDP sendCommand Input.dispatchKeyEvent timed out after
30000ms`). No Generate click ever happened — but when the DEV checked the
page immediately after the timeout, a generation was already in flight:
Unlimited toggle already reset to OFF (from an earlier page reload, as
documented below), Generate button already reading a credit number, spinner
card already active. Best-available explanation: a stray Enter/keydown
leaked out of the failed keystroke dispatch queue, and the composer treats
Enter-in-composer as submit. Cost **1 real credit**, auto-refunded by
Higgsfield the same minute (`1 credit · Seedream 4.5 · Spent` then `+1
credit · Seedream 4.5 · Refunded`, both timestamped same minute — net $0,
but a real paid generation fired with zero deliberate action to gate
against it, which the existing hard rules did not anticipate).

**Root cause, confirmed** (superseding the original stray-Enter hypothesis):
`type()` truncated the prompt to its first sentence in three separate
generations that session (8:03 PM, 8:05 PM, and again at 9:16 PM even
after switching to a shorter prompt) — confirmed each time by reading the
generated card's own Info/Prompt panel, which showed only the opening
line, not the full character description. The mechanism is `type()`
itself, not a downstream Enter/submit side effect: a keystroke-simulating
type action against this Lexical editor is not reliable for multi-paragraph
text, full stop. **Validated fix**: switch to synthetic `ClipboardEvent`
paste only (see hard rule 6) — confirmed clean in the same session (source
781 chars; three independent reads at 790/787/775, correct first/last 80
chars, no truncation). Reference: mooniex-agents task-7b4402d4.

## Reading the credit ledger — screen by magnitude, not by model name

The account total is **cumulative and shared**, so it rises for reasons that
have nothing to do with the video pipeline. Chasing it as a single number
produces false alarms: on 2026-08-13 it read 339.2 credits / $13.568 against
a 21.8 / $0.872 baseline confirmed the day before — a 15x jump that looked
alarming and was entirely benign.

**Unlimited covers Seedance video only. Images are always charged.** Every
reference plate the CEO builds is a paid image create, and plates are made by
the dozen with retries.

Known price points (CEO, 2026-08-13):

| What | Cost |
|---|---|
| Image create, GPT Gen2 | **0.2 – 2 credits** |
| Seedance 2.5 video, Unlimited Mode | **0** (entry reads `Unlimited`, no digit) |
| Seedance 2.5 video, accidental Rerun | **130 credits** |
| Credit rate | $0.04 / credit |

That table is the audit's first filter: **a video charge is 65x the ceiling
of an image create, so it is unmistakable by size alone.** Do not try to
identify charges by model name — names in the ledger are ambiguous and
paginating for completeness is expensive. Scan for entries of **5 credits or
more**.

**Then apply the second filter, which is the one that actually decides:
compare each hit's DATE against the window your own wave has been running.**
Size tells you an entry is a video charge; only the date tells you whether it
is *yours*. Skipping this step makes the audit useless, because the ledger
permanently contains historical video charges and always will:

| Entry | Date | Verdict |
|---|---|---|
| 130 credits · Seedance 2.5 | 2026-08-10 22:18 | Known Rerun incident — task-eed61860, GH #45 |
| 72 credits · Seedance 2.0 | 2026-08-05 15:44 | Refunded +72 at 15:49, net 0 |
| 72 credits · Seedance 2.0 | 2026-08-05 | Same day, same class |

An operator running the size filter alone will find those three every single
time, conclude "not clean", and halt a wave that has spent nothing. That
happened on 2026-08-13 and cost a full stop plus a round trip. **A charge is
only an incident if its timestamp falls inside a window when an operator
clicked Generate.** Give the DEV the wave's start date and let it clear
historical hits on its own instead of escalating them.

Sizing sanity check from the same day: ~317 credits of image spend over 35
plates is ~9 image creates per plate at ~1 credit each — the total reconciles
with zero video charges of our own.

**The baseline is not necessarily cumulative.** The 21.8 credits / $0.872
figure carried as "the baseline" through this wave could not have been a
cumulative spent total, since a 130-credit charge two days earlier would
already exceed it. It was a different view — a period or page subtotal — and
treating it as the same metric as a 339.2 cumulative reading produced a
phantom "15x jump". Before comparing two ledger numbers, confirm they are the
same view.

**What still matters when the total moves:** not the total, but (a) every
Seedance 2.5 entry still reading `Unlimited` with zero digits, checked
immediately before each Generate click, and (b) no charged entry landing
inside a window when an operator clicked Generate. Re-baseline freely; the
baseline is a reference point, not a budget.

## Hard rules — non-negotiable, no exceptions

1. **Never click "Rerun"** (↻ icon, bottom-left row on a History/generation
   card). Banned entirely on every Higgsfield task, forever. It auto-fires a
   generation with no confirmation.
2. **Use "Recreate" instead** (copy icon, top-right of the video thumbnail,
   appears on hover — confirm via its tooltip text before clicking) to load
   a card's prompt + references into the composer for editing. This does
   NOT fire anything by itself.
3. **Before every single Generate click, with no exceptions**: zoom into the
   Generate button itself and confirm it reads bare **"Generate"** with
   **ZERO digits anywhere on it** (not "Generate ✦ 130", not any number). If
   any number shows, do not click — stop and message the C-level. The
   Unlimited Mode toggle's apparent on/off state is **not sufficient on its
   own** — it silently resets to OFF after any full-page reload, which is
   the exact gap that caused the incident above.
4. **One generation at a time.** Wait for full completion (card shows
   Recreate+Rerun options and full resolution/duration/aspect-ratio
   metadata, no "Processing"/"Generating" state) before starting the next.
   No parallel generations, ever.
5. **Concurrency toast with no visible in-flight job**: if Higgsfield shows
   a "1 unlimited generation at a time" toast and nothing in your own
   History is actually generating, don't force through it or guess a
   workaround. Message the C-level and wait.

6. **If the Unlimited toggle won't respond, stop after the FIRST clean
   attempt — do not escalate through more click techniques.** Real incident,
   2026-08-14 (task-f693a4ee, GH #67): the toggle was stuck off, so the
   Generate button stayed priced (`Generate180135`) for the whole session.
   The operator never intended to click it and correctly never clicked it
   on purpose — but while troubleshooting the toggle it tried seven
   different techniques in succession (ref click, raw-coordinate click,
   keyboard focus+Space+Enter, click-drag, hover, double-click, zoom+click),
   and **two real 135-credit charges landed anyway**, $10.80 total, most
   likely because one of those techniques — probably the keyboard Enter
   press — landed on the adjacent Generate button instead of the switch
   (the two sit 40–50px apart). Every click technique tried near a priced
   Generate button is itself a money risk, independent of what you're
   aiming at.

   **The fix:** one ref-based click attempt on the exact toggle element via
   `find()`. If `data-state` doesn't flip, **stop entirely and message the
   C-level** — do not try a second technique, do not try raw coordinates,
   do not try keyboard input near the composer. A stuck toggle is a
   blocker to report, not a puzzle to solve by trying more input methods
   next to a live priced button.

   **Standing escalation policy, CEO-set 2026-08-14: any control an
   operator cannot reliably click goes to the CTO, not back into more
   operator retries.** The CTO asks the CEO to fix it by hand in the real
   Chrome window. The operator's job at that point is to **leave the
   browser open exactly as it is** — no navigate, no refresh, no retry, no
   close — and report the composer's exact current state (text present,
   element chips attached, toggle state) so the CEO knows what he's
   looking at before he touches anything. **The CEO clicks Generate
   himself in this scenario, not the operator** — the final money-
   committing click moves to a human hand whenever the automated path has
   already failed once. This generalizes past the Unlimited toggle to any
   stuck control on a priced surface.

   **What actually causes it** (measured 2026-08-12, task-cda4f469): the
   slot is **account-wide, not project-wide**, and a generation survives the
   death of the agent that started it. Killing a DEV does not cancel its
   in-flight render — that job keeps running server-side and keeps holding
   the slot until it finishes on its own, roughly 20 minutes for a
   20-second Seedance clip. So the toast is the normal, expected state for
   ~20 minutes after any operator is killed mid-render, and it resolves
   itself with no action.

   Two checks resolve it, both read-only:
   - Look at the **account-level** generations feed, not just the current
     project's History. A job in any other project on the account holds the
     same single slot and is invisible from inside one project.
   - Find the most recent Usage entry and work out whether it is still
     running. If its timestamp is under ~20 minutes old, that is the
     holder; wait it out.

   The toast costs nothing — the click that triggers it does not generate
   and does not move credits, confirmed. A retry after the wait is safe;
   forcing it or hunting workarounds is what is banned.
6. **Never enter prompt text with a keystroke-simulating "type" action.**
   Confirmed 3-for-3 failure rate in one session (task-7b4402d4): every
   `type()`-entered multi-paragraph prompt silently truncated to a
   fragment, which then got submitted as a real generation with wrong
   subject matter. Synthetic-paste is the fix, not a style preference — see
   Incident 2. Use `ClipboardEvent` paste **only**, every prompt, no
   exceptions, especially prompts with blank lines between paragraphs
   (most of ours).
   - **Do NOT also dispatch a synthetic `input` event after the paste.**
     Tested and confirmed harmful: Lexical's own paste handler already
     inserts the text, and a follow-up synthetic `input` event causes a
     **second** insertion — the text appears duplicated in the editor.
     Paste alone is sufficient and binds correctly to the framework's real
     state.
   - **FIRST pick the right node — there is a decoy editor.** Measured
     2026-08-12 (task-cda4f469): the composer renders **two overlapping
     `contenteditable` elements**, and a paste aimed at the wrong one lands
     silently with no error and no visible text. The reliable tell is
     **`getComputedStyle(el).visibility === 'hidden'` on the decoy**. Nothing
     cheaper works: bounding rect, offset position, and the presence of
     `__lexicalTextContent` are **identical on both nodes**, so every naive
     "find the contenteditable" selector has a coin-flip chance of hitting
     the dead one. Filter candidates by computed visibility before touching
     anything.

     This very likely explains the earlier incident where a card's saved
     prompt contained only its first line — at the time it was blamed on
     keystroke truncation. Treat a mysteriously empty or partial saved
     prompt as decoy-editor first, `type()` second.
   - **Verify via three independent reads before every Generate click**:
     `element.innerText`, `element.__lexicalTextContent` (or equivalent
     Lexical-exposed text property), and — the authoritative one —
     `editor.getEditorState().toJSON()` if you can reach the editor
     instance. **These three do not save you from the decoy** — run them on
     the decoy and they agree with each other perfectly, on empty content.
     They only mean something once the visibility check above has selected
     the real node. Compare all three against the source prompt's length and
     first/last ~60-80 characters. `innerText` alone is not enough — it
     can show complete text while the framework's real bound state (what
     actually gets serialized into the Generate API call) is empty or
     truncated. This is the actual mechanism behind Incident 2, not a
     stray-Enter theory (that was an earlier, superseded hypothesis).
7. **Any browser-tool error or timeout while on a Higgsfield generation
   page — of any kind, not just during text entry — means your next action
   is checking Usage History, before anything else.** A timeout does not
   mean nothing happened; the underlying page action may have partially or
   fully completed regardless of what the tool call reported back. Don't
   assume a failed call = no side effect.

## Render time is a function of WHEN you generate — schedule the wave for Europe's night

Measured across a single 14-hour wave on 2026-08-13. Render time is not a
constant and it is not degrading equipment; it tracks the platform's queue
depth, which tracks European waking hours.

| Local (ICT, UTC+7) | UTC | Europe (CEST) | Render |
|---|---|---|---|
| 08:36 – 13:33 | 01:36 – 06:33 | 03:36 – 08:33, night | **20–25 min** |
| 13:57 | 06:57 | 08:57, waking | **137 min, never finished — cancelled** |
| 16:26 | 09:26 | 11:26 | **50+ min** |
| 18:33 | 11:33 | 13:33, midday | worst |

**It does not degrade gradually — it changes at the hour Europe wakes up.**
Every fast clip landed while Europe was asleep; the first pathological render
started at 06:57 UTC and nothing recovered after that.

Practical consequences:

**The window is 01:00–07:00 UTC and nothing else.** Work it out from all three
user bases, not just the one that happened to break the wave:

| UTC | Europe | US East | US West | Load |
|---|---|---|---|---|
| 07:00–16:00 | **working** | morning→afternoon | morning | stacked peak |
| 16:00–01:00 | evening→night | **working** | **working** | US peak |
| **01:00–07:00** | **asleep** | **asleep** | **asleep** | **the window** |

`01:00–07:00 UTC` is **08:00–14:00 ICT** — six hours, about 14 clips at 25
minutes each.

- **Schedule long waves for 08:00–14:00 ICT.** Spawn the operator ~07:30 so the
  first prompt is staged and verified before the window opens.
- **Thai overnight is the WRONG answer** even though it feels like the natural
  time to run an unattended job. 00:00–08:00 ICT is 17:00–01:00 UTC, which is
  US East afternoon plus US West full working day — their peak, not a lull.
  Recorded because that was the first conclusion drawn from this data and it
  was wrong: it fitted the European evidence and ignored America entirely.
- The same queue costs 2–5x more wall-clock outside the window.
- **A slow render is not a bug.** Before investigating anything client-side,
  check the clock. On 2026-08-13 an afternoon went into changing the polling
  method, pipelining prompt setup and restarting Chrome twice, all chasing a
  variable that lived on the platform's side.
- **The 90-minute cancel rule still applies**, but expect to use it far more
  often during European daytime, and expect a normal render to take 50+ minutes
  rather than 25. Do not read that as a stuck card.
- The account's one-generation-at-a-time slot makes this compound: at 25 min a
  20-clip queue is ~9 hours, at 50 min it is ~18, and a single 137-minute
  zombie blocks everything queued behind it.

Credit safety is unaffected — the ledger stayed flat at $0 throughout, and a
slow render costs nothing. This is purely throughput and scheduling.

## A long-lived tab lies about the concurrency slot — open a fresh one every 3-4 generations

The single largest time sink measured on this project, and it looks exactly
like a server-side problem while being purely client-side.

Observed 2026-08-13 across a four-hour session: Generate kept returning the
"1 unlimited generation at a time" toast, with a card apparently stuck on
`Processing` that survived hard reloads. It read as a zombie generation holding
the account slot. **It was not.** A brand-new tab showed every card already
finished, no `Processing` badge anywhere, and the ledger confirmed nothing had
billed. The render had completed long before; the aging tab was holding stale
state for both the badge render and whatever the client consults to decide the
slot is busy.

The same staleness produces two other symptoms that look unrelated:

- **The Unlimited toggle stops registering clicks** — coordinate click, ref
  click and double ref click all leave it at `aria-checked=false`. More clicks
  never help. A fresh tab fixes it immediately.
- **A processing-text check returns "none" and Generate still toasts.** The DOM
  and the true server-side slot state have drifted apart, so the page's own
  evidence is worthless.

**Do not treat any of these as things to wait out.** Waiting cost roughly ten
minutes per clip across a 26-clip queue before the cause was found, and it
corrupted the pace estimate reported upward — what looked like 20-minute
renders was mostly waiting on a slot that was already free.

Rules:

- **Open a fresh tab every 3-4 generations, proactively, before anything looks
  wrong.** Close the old one. This is routine hygiene, not troubleshooting.
- **Never accept these as evidence the slot is free:** the `Processing` badge,
  the absence of processing text, or any cached element reference. A freshly
  loaded tab is the only reliable check.
- **If the toggle reads `aria-checked=false` after a click, go straight to a new
  tab** rather than clicking again.
- Escalation order stays: hard reload → new tab → quit and reopen Chrome.
  Chrome belongs to the org, so restarting it needs no permission.

## The composer silently resets its settings — check the spec, not just the price

Hard rule 3 covers the Unlimited toggle resetting to OFF. **It is not the only
control that drifts.** Observed 2026-08-13 on Scene 9C: the resolution had
silently reverted to **480p** between generations, caught only because the
operator re-read the settings before clicking rather than trusting them.

This is a different class of failure from the credit rules, and more
insidious, because nothing stops it:

- A 480p clip **completes normally**, shows a normal card, downloads normally,
  and mirrors to Drive normally.
- It costs nothing, so no money check catches it.
- It is off-spec footage that surfaces at **edit time**, after the account's
  one-at-a-time serial slot has already been spent producing it.

**Re-verify the full spec immediately before every Generate click**, the same
way the zero-digit price check is done — not just the Unlimited toggle. For
this project the locked spec is **20s / 720p / Seedance 2.5 / High / Sound ON**
(CEO: *"ปรับ ค่าเป็น 20s 720p Seedance 2.5 High 1/4 SOund ON Seedance 2.5 เสมอ"*).

Also read it back on **completed** cards, which display their real resolution
and duration: a clip generated off-spec earlier is invisible until someone
looks for it.

**What Unlimited is actually saving:** on the same day, the toggle struck a
20s/720p Seedance 2.5 generation from **450 credits to 0** — $18 a clip at the
$0.04 rate. That is the concrete stake behind the zero-digit check, and a
useful "before" value: 450 struck through means the toggle is working; 450
*not* struck through is $18 about to leave the account.

## Editor gotchas (Higgsfield's prompt box is Lexical/contenteditable)

- **Clearing**: use a real Cmd/Ctrl+A + Delete keypress via the driving
  tool. `document.execCommand('selectAll')`/`delete` does **not** actually
  clear it — measured behavior is append, not replace.
- **Entering text**: synthetic `ClipboardEvent` paste with
  `DataTransfer.setData('text/plain', ...)` **only**. Also setting
  `text/html` causes a double-paste bug (content inserted twice). Verify the
  resulting text length before ever touching Generate.
- **A correct paste can still fail to reach the app's form state.** Measured
  2026-08-12 (task-cda4f469): Generate was refused four times in a row with
  the literal error **"Prompt > Instruction: Prompt is required"** while the
  editor demonstrably held the text — read-back gave `innerText` 2216 chars
  and `__lexicalTextContent` 2417 chars, correct content, right node, decoy
  already filtered out. The paste reaches Lexical but never binds to the
  React state Higgsfield validates against, so the app believes the field is
  empty. **Do not read this error as a content rejection or a bad prompt** —
  the identical text had generated successfully minutes earlier. It showed up
  specifically on the *second consecutive submission of the same prompt*.
- **For any repeat of a prompt that already generated once — a spare, a
  retry, a second variant — do not paste at all. Use Recreate.** Hover the
  successful card's thumbnail, confirm the tooltip reads Recreate (never
  Rerun), and click it. Higgsfield loads its own prompt and references through
  its own code path, which fills the form state correctly by construction: no
  paste, no decoy, no desync. Confirmed working immediately after four paste
  failures on the same shot. It is also faster than pasting. If Recreate is
  genuinely unavailable, reload the page fully and paste into a clean
  composer.
- **Recreate button reliability**: its on-screen position shifts with
  thumbnail width (cards with different reference-image counts render
  different thumbnail widths), and it only mounts in the DOM on real hover,
  not just CSS-hidden — hover-then-verify via tooltip text every time,
  don't trust a fixed coordinate or a cached element reference. A click can
  also silently no-op even on a DOM-valid reference for no clear reason —
  verify the composer actually loaded the target card's distinctive text
  before proceeding, retry once if not.
- **History pagination**: the list is server-paginated, not just
  virtualized — `scrollHeight` grows as you scroll toward the bottom
  (measured: 24k→48k→72k+ px). Don't assume a fixed scene/card count from
  what's initially rendered; scroll to the true end and re-read before
  concluding "that's everything."

## The render-wait pattern (prevents silent DEV death)

A DEV task once died with zero report and zero checkpoint ~34 minutes after
spawn — worktree files frozen at spawn timestamp, pid no longer running,
watchdog record showing `silent_seconds: 2019`. Root cause: it was waiting
on a self-scheduled wake/notification for the long render (10-16 min
typical per generation) instead of actively polling — that mechanism does
not reliably fire for a spawned DEV subprocess, so it sat silent until an
external watchdog killed it, invisible to the C-level the whole time.
Reference: task-036de9ea.

**Root cause, confirmed 2026-08-12 (task-cda4f469): a spawned DEV's shell
blocks standalone `sleep`.** This is the whole reason the failure keeps
happening. The DEV is told to "wait 10 minutes", discovers it cannot sleep,
and falls back to the one mechanism left to it — a scheduled wake or
background timer — which does not reliably fire for a spawned subprocess. It
then sits announcing its intention instead of doing anything. Two operators
were killed on one wave for this before the cause was found; both had been
reporting "Pacing N minutes, then checking directly" every few minutes
without ever once reading a card. Do not diagnose this as laziness or
insubordination — it is an environment constraint, and the operator usually
cannot see it either.

**Fix — bake all of this into every Higgsfield task brief:**

1. **Never rely on a scheduled wake, background timer, or notification.**
2. **The poll loop IS the wait.** Each cycle, actually re-read the card, the
   Usage page and the target folder. Those page reads take real wall-clock
   time and produce evidence instead of silence. Pacing is a by-product of
   doing the checks, not a thing to arrange before doing them.
3. If a hard delay is genuinely needed, `sleep` alone will be refused — use
   `.venv/bin/python -c "import time; time.sleep(180)"` from the worktree.
   **Cap any single sleep at ~90 seconds and repeat it, never one long block.**
4. **Cadence, CEO-set 2026-08-14: first check ~20 minutes after clicking**
   (a render never finishes before ~20 min, so checking at 10 wastes a turn
   for nothing), **then every 5 minutes.** This governs how often you *look*
   at the render status — the 90s sleep-chunking above is unrelated and
   still applies underneath it, so you stay reachable to messages between
   checks without checking the page itself any more often than this.

**A long sleep makes the operator unreachable, and that is indistinguishable
from a hang.** A foreground sleep blocks the agent's whole turn; messages the
C-level types into the tab sit unread in the input buffer until it ends.
Measured 2026-08-14 (task-0ee4a20a): the operator fired Scene 10-D correctly —
zero-digit check passed, all 10 chips intact — then entered a single
`time.sleep(600)`. Three CTO questions went unanswered across 83 minutes while
the pid stayed alive and the DB heartbeat kept moving. Reaching the same 10
minutes as seven 90-second sleeps would have let it surface and answer between
each one.

**Before treating a silent operator as stalled, read its tab.** It is
non-invasive, costs nothing, and shows exactly what the agent is doing —
including a sleep in progress and how far through it is:

```bash
osascript -e 'tell application "iTerm2"
 repeat with w in windows
  repeat with t in tabs of w
   set s to current session of t
   if (name of s) contains "<task-id>" then return (contents of s)
  end repeat
 end repeat
end tell' | tail -35
```

Do this BEFORE pinging again and long before killing. In the case above it
immediately showed a correct Generate click and a running sleep; the C-level
had already sent three unnecessary messages and was one step from killing an
operator that was working perfectly.

**Order of operations matters more than the interval: CHECK → REPORT →
WAIT.** Both dead operators inverted it (announce → wait → wake → announce)
and therefore never checked anything.

**Make the reporting contract mechanical, not adjectival.** "Report concrete
state, not intent" is too vague — an operator will read "Pacing 6 minutes,
then re-checking" as concrete. Instead require three literal values in every
message, including when nothing has changed:
- the literal text on the card being watched,
- minutes elapsed since the Generate click,
- the current Usage total, as a number, against a stated baseline.

A message that lacks those three is a failed report regardless of how
detailed it otherwise looks.

## Operating pattern for multi-generation jobs

- **Split into waves capped at ~5 generations each — this is a hard cap, not
  a suggestion.** Spawn a separate task/DEV session per wave rather than one
  long-running session. Screenshots stay in context for the rest of a session
  and get re-sent every later turn — capping wave size caps that growth, and
  every extra turn a long-lived DEV takes costs more than the last one because
  its own history keeps growing. **Missed 2026-08-14**: a 14-clip / 7-scene
  queue was handed to one task instead of split into three ~5-clip waves; the
  CEO caught it live and had it split mid-flight. When writing a task brief,
  count the clips before delegating — if it's more than ~5, split it before
  spawning, not after.
- **Maintain a reusable replay-helper script**
  (e.g. `scripts/browser/higgsfield-jumpcut-gen.js`) covering the mechanical
  flow: locate card → clear+paste prompt → verify zero-digit Generate
  button → click → poll. It deliberately does **not** auto-click
  Recreate/Unlimited-toggle/Generate itself — those three stay under a
  model's live tooltip/visual confirmation on purpose, since automating
  them away would defeat the safeguard that exists because of the incident
  above. Each wave should read this script first and append new findings to
  it (numbered, dated) rather than re-deriving technique from scratch.
- **Scope discoveries are a C-level decision, not a DEV guess.** If a DEV
  reports something that changes scope (a scene count that doesn't match
  the brief, an undocumented content set sitting in History) — surface it
  plainly to the CEO/C-level and get an explicit call before generating
  anything against the new information. Don't reconcile it yourself.

## Task-brief checklist

When writing a `create_task` description for a Higgsfield `browser_operator`
task, include:
- [ ] The 7 hard rules above, verbatim or paraphrased — especially the
      Rerun ban, the zero-digit Generate check, paste-only text entry, and
      the check-Usage-History-after-any-error rule.
- [ ] The editor gotchas if the task involves writing new prompt text.
- [ ] The 10min → 5min → 3min-repeating poll schedule for any render wait.
- [ ] Explicit scope boundaries — what NOT to touch (other scenes, other
      projects mixed into the same History, the tracking artifact).
- [ ] Stop-and-ask conditions: any number on the Generate button, an NSFW
      flag repeating, a result needing creative/brand judgment, anything
      about the page behaving unexpectedly, any browser-tool error while on
      a Higgsfield page.
- [ ] Pointer to the existing replay script if one exists for this project.

## Reference

- Incident + full fix history: mooniex-agents task-eed61860 (Wave 1, credit
  incident), task-1ecf3dd2 (Wave 2), task-76d3ce0d (Wave 3), task-036de9ea
  (Wave 4, silent-death incident), task-7b4402d4 (keystroke-timeout
  auto-fire, Incident 2 above). GH issue #45, #47.
- Related skills: `browser-operator` (generic browser cost-discipline),
  `dev-spawn-protocol` (generic DEV spawn steps).
