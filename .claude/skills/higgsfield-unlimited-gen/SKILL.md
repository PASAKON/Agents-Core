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

## UNLIMITED COVERS SEEDANCE 2.5 VIDEO ONLY. IMAGES ALWAYS COST CREDITS.

**CEO, 2026-08-27, stated directly: "เรา Unlimited แค่ 2.5 Seedance"** — our
Unlimited applies to Seedance 2.5 and nothing else, and it has an end date he
has already given. **GPT Image 2 is NOT Unlimited and never was.**

This section previously claimed the opposite ("Unlimited covers IMAGES too —
corrected 2026-08-19… do not tell an operator to expect a charge on plates").
**That was wrong and it cost real time.** On 2026-08-27 an operator read it,
went looking for an Unlimited toggle beside GPT Image 2, found the paid
*upsell* control that sits there, saw it open a $30 purchase page, and
correctly refused to buy — then stalled for eight minutes filing a blocker
against a system that was working perfectly. The whole detour came from this
file.

| What | Covered by Unlimited? | Real cost |
|---|---|---|
| **Seedance 2.5 video** | **YES** | 0 — button reads `UNLIMITED`, price struck to 0 |
| **GPT Image 2** (every plate) | **NO** | ~3 credits at 2K/Medium, ~2 at 1K/Medium |
| Any other model | NO | metered |

Two consequences an operator must internalise:

- **On a VIDEO generate, any live number at all means STOP.** The only safe
  reading is struck-through-then-zero.
- **On an IMAGE generate, a small live number is CORRECT, not a fault.** About
  3 credits is what a plate costs and what every plate in this production has
  cost. An operator that halts on it is halting on normal operation.

**There is an "Unlimited mode" control next to GPT Image 2. It is a paid
upsell, not our subscription. Never click it.** It is not the toggle the rest
of this skill is about; that one lives on the Seedance 2.5 composer.

Give image tasks an explicit credit budget in the brief (e.g. "12 credits =
four attempts") so the operator knows a charge is expected and knows the
ceiling. Name 1K/Medium explicitly if cost matters, or the composer defaults
to something dearer.

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
4. **One UNLIMITED VIDEO generation at a time.** Wait for full completion
   (card shows Recreate+Rerun options and full resolution/duration/aspect-ratio
   metadata, no "Processing"/"Generating" state) before starting the next
   video. No parallel video generations, ever.

   **But a paid GPT Image 2 generation does NOT contend for that slot, and
   holding image work behind a rendering video wastes hours.** Measured
   2026-08-28 on the «Sorry, Sir» wave: Scene 2 fired as an Unlimited
   Seedance video at 05:50 and was still rendering at 06:30, and during that
   window **two separate operators each fired and completed a paid image
   plate** — `char_grandmother` (asset `5dd23a87`) and `char_gentleman`.
   Neither saw a concurrency toast.

   The slot is scoped to **unlimited** generations. Paid ones queue
   independently. The CTO on that wave stood two image operators down "until
   the video clears" and burned roughly forty minutes of two workers for
   nothing — do not repeat it. **Video work serialises; image work runs
   alongside it.**
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

   **Once the CEO has fixed the toggle by hand, that composer tab becomes
   protected — proceed on it, but never navigate it away, refresh it, or
   close it, for the rest of the session.** A page reload silently resets
   Unlimited back to off (already documented above as the cause of the
   original incident), so leaving this exact tab would force the CEO to
   walk over and click it by hand a second time — an avoidable ask. Need
   to check Usage, History, or anything else mid-queue? **Open a separate
   tab for that** and leave the composer tab exactly as the CEO left it.

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
   - **THE DECOY IS NOT ONLY THE PROMPT BOX — THE DURATION FIELD HAS IT TOO.**
     Measured 2026-08-28 on the «Sorry, Sir» wave, at a cost of four unusable
     clips. It is a plain freeform `contenteditable`: no `<select>`, no slider,
     no option list, and the same overlapping duplicate structure.

     The signature is **two fixed output values and no error at all**:

     | Clip | Target | Actual |
     |---|---|---|
     | S2, S3 | 20s | **20.04s** |
     | S4, S9, S17, S18 | 15 / 20 / 25s | **11.04s every time** |

     The decoy accepts the typing, echoes the value back when read, and sets
     nothing; the real field keeps its default. Because it reads back
     *correctly*, a read-back check alone does **not** catch it — read back from
     the node you selected by visibility, or you learn nothing.

     Three false diagnoses were burned before anyone inspected the DOM: a stale
     tab (a fresh tab reproduced it on the first attempt), a lapsed Unlimited
     entitlement (plan active, usage log all `Unlimited` with no digits), and a
     platform-side duration cap. **A clean two-valued result with no error is a
     decoy signature, not a cap.**

     **Apply the visibility filter to every contenteditable in that composer,
     not just the prompt box.**
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
- **A tab whose viewport has collapsed to a stuck 728x420 "mobile" layout
  cannot be repaired — open a fresh tab.** Measured 2026-08-27
  (task-f4305098): `resize_window` returned success and changed nothing, so
  the operator had no error to react to; the page kept rendering the mobile
  composer, where several controls do not exist at all. Treat a success
  return from `resize_window` as unverified until the layout actually
  changes, and skip straight to a new tab.
- **Clicks can stop registering across the whole tab, ref-based ones
  included.** Same session. Nothing errors — every call reports success and
  the page simply never responds. If two consecutive clicks produce no DOM
  change, stop clicking and hard-reload; more attempts near a priced
  Generate button is exactly the pattern that cost $10.80 in the toggle
  incident above.

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
- **A full page reload does NOT clear the desync on its own** — measured
  2026-08-27 (task-f4305098), directly contradicting the fallback sentence
  above, which was written from a session where the reload happened to
  coincide with a recovery. The operator reloaded fully, pasted into a clean
  composer, and Generate still refused with the same "Prompt is required".
  **What actually forced the bind was a real trusted keystroke after the
  paste: `End`, then `space`, then `Backspace`.** A synthetic paste alone
  never produces the keydown React listens for; those three keys leave the
  text byte-identical while generating genuine trusted key events, so the
  bound state catches up to the visible text.
- **Make the three-key tap a routine step after every paste**, not a
  recovery move — it costs one call and removes the whole failure class
  before you ever look at the Generate button. It does not conflict with the
  ban on `type()` for prompt *content*: the ban exists because keystroke
  entry truncates multi-paragraph text, and these three keys enter no text
  at all.
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

### Pre-stage the next prompt during the wait — CEO rule, 2026-08-14

Loop, per clip: **click Generate on clip A → immediately paste clip B's
prompt into the composer, staged and ready, while A renders → sleep on the
20-then-5min cadence above → when A's card completes, click Generate on the
already-staged clip B prompt right away → repeat, staging clip C during B's
render.**

The point is to spend the render's dead time on next-prompt prep instead of
doing that work cold after waking. Editing the composer text box does not
touch the in-flight render (A is already committed server-side) and does
not touch the Unlimited toggle, so this is safe to do inside the protected
composer tab.

**Staging early does not relax the checks that happen at the actual click.**
Re-verify the zero-digit Generate button and the element count fresh at the
moment you click B, exactly as if it had just been pasted — do not treat
"I already checked this when I staged it" as sufficient. The checks exist
because state can change silently; a prompt sitting staged for 20+ minutes
gets no exemption from that.

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

- **Never let the Unlimited slot sit idle — CEO rule, 2026-08-14.** Seedance
  2.0 / 1080p / 15s runs **~30 minutes per clip on average** — the CEO's own
  figure, stated as the reason every idle minute is expensive even though
  the credits are free. The moment a card finishes, fire the next one
  immediately. Unlimited generation costs nothing, so an idle slot is pure
  wasted time, not saved money. If the *next scripted item's* prompt isn't
  ready yet — the CTO is
  still writing it — **do not wait idle for it.** Generate whatever *is*
  already written and ready instead (a spare take of a scene already
  generated, or any other queued item that has real prompt text), then
  come back to the scripted order once the CTO catches up. Example the CEO
  gave: the CTO is still writing Scene 12, but a spare take of Scene 11 is
  ready to fire — fire that, don't sit waiting on 12. Only stop firing
  entirely when nothing anywhere is ready to generate.
  **No permission needed for this, and it isn't capped at one extra take
  either** (CEO, same instruction, elaborated): while waiting on the next
  scripted prompt, re-generate an already-written scene as many times as
  useful, past the normal real+spare pair, since Unlimited costs nothing.
  If that scene needs 2 footage variants, generating more than that during
  idle wait time is fine too — more usable footage for the editor, at zero
  cost, is never wasted. Keep every extra take, same as always.
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

## Findings from the Valder wave, 2026-08-19 — every one of these cost a live blocker

An overnight wave on `ai-film-festival-3` (project `project_valder_*`) stalled
five separate times on UI behaviour that no brief anticipated. Each item below
is the fix, already paid for.

### The video Generate button shows a struck-through price. That is correct.

**Do not carry the "zero digits" rule over from image tasks.** On a Seedance
video generation with Unlimited active, the button reads
`Unlimited · ~~140~~ · 0`. The struck-through number is the price you are *not*
paying and the `0` is what is charged. A struck-through price is positive
evidence the toggle is working.

| Button reads | Meaning |
|---|---|
| struck-through price then `0` | Unlimited working — **click** |
| bare `Generate`, nothing else | fine — **click** |
| live price, NO strike-through | Unlimited OFF — **do not click** |

**The distinction is the strike-through, not the presence of digits.** A brief
that says "zero digits anywhere" will stop a correct operator dead; one that says
"any number means stop" is worse, because it trains the operator to ignore the
real signal. Write the table.

### SEEDANCE 2.5 TAKES UP TO 50 REFERENCES. Not 9. Design scenes accordingly.

CEO, 2026-08-27: **"Higgsfield ได้มากสุด 50 REF"** — and he had said it before,
which means a CTO planned around a nine-element ceiling that does not exist and
wrote weaker scenes because of it.

**The ceiling for Seedance 2.5 is 50 references.** Any earlier note in this org
claiming nine is wrong. Do not ration references.

#### What this unlocks — one reference per person

With 50 slots, **every character who does anything gets their own individual
plate.** No group plates for anyone who acts.

That is not a nicety, it is the difference between directing and hoping. A group
plate of eight people cannot be directed: write "one of them raises a hand
toward the wall" and the model has no idea which one, so it invents. With one
plate per person you write `@char_critic raises a hand toward the wall while
@char_student shakes her head` and both land.

CEO's rule, verbatim: **"REF ที่ดี ต้องมี 1 REF / 1 คน / 1 ภาพ"** — one
reference, one person, one image. **"แม้แต่ตัวประกอบ ก็ต้องมี REF"** — even the
extras.

Group plates still have one honest use: an undifferentiated mass in the deep
background that performs no action. The moment a body needs to do something
specific, it needs its own plate.

### THE EASY WAY TO ATTACH A REFERENCE: DRAG THE ASSET IN, THEN USE @Image1 / @Image2

**Read this before doing anything with Elements.** It is simpler than everything
below it and it sidesteps the entire Element-naming problem.

Reported by the CEO from the live UI, 2026-08-27, after an operator had spent
hours fighting red tags:

> "2 Image นี้มีอยู่แล้วในนั้น ใช้เป็น Ref ได้โดยการลากมาวาง ไม่ต้อง Create
> Element ID หลังจากลากวางใช้ @Image1 + @Image2 สำหรับอ้างอิง"

**Any image already in the project can be dragged straight into the composer and
used as a reference. No Element needs to be created and nothing needs a name.**
Once dropped, the images are addressed positionally in the prompt text as
`@Image1`, `@Image2`, and so on, numbered in the order they were dropped.

```
1. Find the asset in the project grid.
2. Drag it into the composer's reference area and drop it.
3. Repeat for each reference you want.
4. Write the prompt using @Image1, @Image2 … to refer to them.
5. Generate.
```

#### Why this matters more than it sounds

Everything else in this file about attaching references — creating an Element,
naming it exactly, typing `@project_name_thing`, watching for red text, the
detail-modal-versus-hover-menu trap, the folder-scoped autocomplete — exists to
solve a problem this mechanism does not have. The named-Element path is for
things you tag repeatedly across many prompts. **For "use this specific image as
a reference right now", drag and drop is the correct tool and it is far more
reliable.**

Two full nights on this project were lost to red tags that turned out to mean
"you never created the Element", when the operator could have dragged the image
in and moved on.

#### When you still want a named Element

Named Elements are still right for **recurring cast, locations and props** that
get tagged in dozens of prompts across a film — you want `@project_x_char_valder`
to mean one fixed thing everywhere. Use the named path for those, and drag-drop
for one-off references.

### HIGGSFIELD SOUL DOES NOT ACCEPT REFERENCE IMAGES AT ALL

Measured 2026-08-27 on the «Absence of Meaning» plate chain. **Soul Cinema
cannot take Element references.** This is not a technique problem — the
capability is absent from that composer.

Both paths were tried, one clean attempt each, and both failed:

| Path | Result in Soul |
|---|---|
| Paste the prompt with `@element_name` inside it | Tag stays **plain red text**. Never resolves. |
| Type a real `@` to trigger the native autocomplete | **No dropdown appears at all.** Tag stays red. |

The paste-auto-resolve behaviour documented further down this file is real, but
it was measured on the **Seedance / video composer**. Soul is a different
composer and does not share it. Do not assume a technique carries between them.

#### What this costs you, and the rule

A red tag generates silently: the model never sees the reference, invents
something plausible from the prose, and the output looks perfectly fine. On this
project it produced a brass plaque that was a completely different object from
the reference plate — different proportions, different typography, missing the
screws — and noticing that mismatch was the only reason anyone caught it.

**CEO's standing ruling, 2026-08-27: if a plate needs reference images, generate
it with GPT Image Gen 2, not Soul.** A bound reference matters more than Soul's
photographic quality, because plates that have to intercut inside one film have
to actually match each other.

This overrides the model-routing rule (Location → Soul, Character/Prop → GPT
Image Gen 2) where the two collide: **routing by asset type loses to the
reference requirement.** A location that must inherit from an earlier plate goes
to GPT.

And whichever way you go, **the whole set goes together** — never one location
from Soul and another from GPT. Different models give different light, texture
and colour response, and a film whose locations came from two models will not
cut together; viewers feel some shots are not the same place without being able
to say why.

Soul remains the right choice for a location that stands alone and needs no
reference.

### RED tag text in the composer = the Element does not exist. Look at the colour.

Spotted by the CEO from a screenshot, 2026-08-27, after an operator spent a
whole cycle generating against references that were never attached.

**A resolved tag renders as a mention chip. An unresolved tag stays as plain
text in RED.** That colour is the fastest, cheapest check available and it is
visible without zooming:

| What you see | What it means |
|---|---|
| Tag rendered as a chip / thumbnail appears in the reference strip | Bound. Good. |
| **Tag still plain text, coloured RED** | **Not bound. The Element does not exist under that name.** |

**Check the tag colour before every Generate.** A red tag means the model never
sees that reference — it silently generates from the prose alone, produces
something plausible, and the failure is invisible in the output.

#### The cause is almost always this: generating an image is NOT creating an Element

These are two separate steps in Higgsfield and it is easy to do the first and
believe you have done the second:

1. **Generate an image.** It lands in the project's asset grid. At this point it
   has an asset id — and **no Element name at all.** `@your_name` will not
   resolve to it, because there is nothing to resolve.
2. **Create an Element from that image and NAME it.** Only now does the plain
   `@name` tag bind.

An operator that generates ten plates and never does step 2 has ten images and
zero usable references. Every prompt tagging them comes out red.

**So: after generating any plate that a later prompt will tag, create the
Element and name it immediately, then verify by typing the tag and watching it
become a chip.** Do not batch the naming for later — the whole point of a
chain-of-reference build is that each plate is attachable by the time the next
one is generated.

See also the Element-creation path below: use the detail-modal route, never the
grid hover menu.

### The @ dropdown is folder-scoped — but PASTE is not. Paste the whole prompt.

Typing `@project_valder_char_son` in the Scene-1 folder composer silently
returned nothing, even though that Element existed and resolved fine in its own
folder. The composer's `@` autocomplete is **folder-scoped**.

That finding is real, and for most of one wave it was read as "cross-folder
elements must be attached through the Elements panel." **That conclusion was
wrong, and acting on it cost more time than the original problem.** Measured
2026-08-19 across three consecutive clips: a plain-text paste whose body already
contains the literal `@project_valder_*` strings **auto-resolves every one of
them into real attached reference thumbnails, across folders**, with no Elements
panel involved. Reference counts came out 9 / 8 / 8, matching each source card
exactly.

**Default flow — use this:**
1. Clear the composer (real Cmd+A then Delete, including leftover mention chips).
2. Paste the entire prompt in one synthetic `ClipboardEvent`, tags included.
3. Count the reference thumbnails.
4. Generate.

**Fallback, only when the tag text is genuinely absent from the prompt:**
1. Open the Elements panel.
2. Find the element's card (switch tabs — Characters / Locations / Props).
3. **Right-click the card → "Use".**

A small warning icon may appear on the reference thumbnail immediately after
attaching. It is transient and clears itself — re-check before treating it as a
failure.

**Do not build a prompt by inserting elements first and typing text around
them.** It attaches the references in an order that does not match the source
text, and on 2026-08-19 a whole composer had to be torn down and re-pasted
because of it. Text first, always; the tags carry themselves.

Related: the folder-scoped Elements picker also **under-reports what exists.**
To see everything on the account, open the project root with `?elements=1`.

### Creating an Element: use the detail-modal path, never the grid hover menu

The folder-grid hover `...` menu is unreliable — the composer's floating
prompt-preview panel overlaps it and swallows the click. What works every time:

click the card → it opens `?preview=<uuid>` → the `...` at the **bottom-right of
that modal** → Create Element.

And the New Element dialog's **Name / Element ID inputs do not accept coordinate
clicks.** Set them with a native value setter plus an `input` event dispatch via
JS. That is a single atomic set, not char-by-char, so it is not a `type()` risk
and it is approved.

### Element IDs are GLOBAL across the account

A short name like `@Mother` resolves to whichever element on the whole account
owns that name — usually one from an older project — and the clip renders with
the wrong face while looking completely normal. Nothing errors.

Every element needs a **Name** (human label) and an **ID** (what goes in the
prompt, all lowercase). Prompts always reference the ID. Convention adopted
2026-08-18: `project_<slug>_char_*` / `_loc_*` / `_prop_*`.

When renaming an existing sheet, replace suffixed tags first (`@Father-Scarf`
before `@Father`) or the shorter token eats the longer one.

### The worker mailbox delivers notifications with no body

Hit repeatedly across five operators in one night: the agent sees
`[New message from CTO]`, reports "no visible content to act on", and goes back
to sleep. Two operators burned 30–45 minutes each waiting on replies that had
already been sent.

**Reply through channels the operator actually reads:**
- **Append to its `TASK.md`** in the worktree. This worked every single time.
- **Comment on the GH blocker issue** it filed — operators poll their own issue.
- Send the mailbox ping too, but only as a pointer: "read the end of TASK.md".

Write this into the brief itself so the operator knows to re-read TASK.md when it
gets an empty notification.

### Do not let a non-generating task hold the queue

An Element-registration task ran 30 minutes without touching the generate slot
while the account sat idle. Registration, verification and reporting are all
free — schedule them *during* a render, never instead of one. If a task's
remaining work does not generate, and something generatable is ready, stop it and
fire the generation.

### Treat "Unlimited is broken" from an operator as unconfirmed

One operator reported the toggle stuck in both its original tab and a fresh tab,
which triggered a switch to paid generation. The CEO checked personally minutes
later: the account was fine the whole time. It was client-side state in that
operator's browser.

Before accepting a broken-toggle report and changing the cost model, get a human
to confirm on the real screen. The recovery ladder stays: one ref click → one
fresh tab → stop and escalate. But escalate as "this operator cannot flip it",
never as "the account is broken".

## Two brief-writing rules learned 2026-08-19 — both cost real time

### Never make a worker sit and watch a render

A generation runs server-side whether or not anyone watches it. A worker parked in
a 90-second sleep loop for 25 minutes produces nothing, burns context, holds a tmux
session, and loses everything it knows if it dies. **A worker's job ends the moment
the generation is confirmed fired.** Checking the finished clip is a separate, cheap
action the C-level does later on a timer.

One exception: if the fire is *not* confirmable, the worker stays until it knows one
way or the other. An unconfirmed fire is the one state nobody can reconstruct after
the fact.

**Better still — warm up the next job during the render** (CEO's idea, and the
sharper version of the same insight). Setup is what costs wall-clock: opening a tab,
setting model/duration/resolution/quality/aspect/sound/Unlimited, pasting a
7,000-character prompt, waiting for mentions to resolve, counting thumbnails,
verifying every field. All of that can happen while the previous clip renders, so
the actual order collapses to *read the price, click*. If there is an approved next
job, stage it; if there isn't, report and exit.

This also names the real bottleneck: warm-up only has something to chew on if
approved prompts are queued ahead of the render slot. Run the storyboard pipeline
ahead of the video pipeline, always.

### Prune the safety gates, or they compound into an hour

Every gate in this skill was bought with a real incident, and the natural instinct
is to add one each time and never remove any. On 2026-08-19 that instinct turned a
single Generate click into **50 minutes**: verify four settings fresh, re-find the
button rather than reuse a ref, open a separate tab to check for stale state, walk a
two-branch decision tree, reapply the desync fix. Every one of those was individually
justified. Stacked unconditionally, they were absurd, and the generate queue sat idle
the whole time.

Split them, and run only the first group every time:

- **Money gates — always, no exceptions.** Read the price on the button immediately
  before the click. Confirm the reference thumbnail count. Confirm the quantity
  stepper. These prevent spending, and spending is not recoverable.
- **Diagnostic gates — only when something already looks wrong.** Fresh-tab
  stale-state checks, decision trees for branch cases, re-verifying settings that
  were verified two minutes ago and nothing has touched since. These are for
  debugging a symptom, not a preflight ritual.

When a brief grows past roughly a screen of checks, that is the signal to prune,
not to add. And say in the brief which gates are mandatory and which are
conditional — a worker given a flat list will run all of them, correctly, forever.

## Hard caps — count before delegating, not after

Folded in from the org memory index 2026-08-25 (the rest of that note was
already covered above; these three numbers were not).

- **Element cap on Seedance 2.0 is 9, not 10.** Confirmed 2026-08-14. A tenth
  element is silently refused, not warned about.
- **Wave cap is ~5 generations, and it is a hard cap, not a suggestion.**
  CEO-enforced 2026-08-14 after a 14-clip / 7-scene queue was handed to a
  single task and had to be split mid-flight. Count the clips before
  delegating, not once the worker is already running.
- **Cap any single `sleep()` at ~90s.** A longer one blocks the poll loop past
  the point where a finished render can be noticed promptly.

## A bound reference keeps the OLD asset when you re-point its Element

Measured 2026-08-27 (task-66d5a582), and it is the most dangerous failure on
this list because **nothing errors and the finished clip looks fine** — it is
just the wrong film.

A reference binds to a specific **asset** at the moment you attach it, not to
the Element name. Re-pointing that Element afterwards updates the Element and
leaves the attached reference exactly as it was. The chip stays green. The name
still reads correctly. Only the thumbnail betrays it, and only if someone looks.

On this job four Elements were re-pointed to regenerated plates during a single
staging session. Two of them — the recast critic and the recolored student —
were still showing the replaced versions in the strip minutes before Generate.
Firing would have produced a scene starring two characters the CEO had already
rejected, with no error anywhere to explain it.

**The fix is never a refresh.** Remove the reference completely and re-add it,
so it binds to the current asset.

**Fold this into the fire sequence**, next to the warning-triangle scan:

> Before Generate, zoom EVERY reference thumbnail and confirm it shows the
> version you actually intend. Any plate regenerated during this session is
> suspect by default — remove and re-add it rather than trusting the chip.

The tell to watch for is a plate that has been through several versions in one
day. A first-generation Element is safe; a re-pointed one is not.
