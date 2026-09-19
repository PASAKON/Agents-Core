# Flow shot runner — iteration 2 (task-a09ed18a)

Continues task-6eabea66 (merged c51d7500). Three parts: two new CLI flags,
a live dry-run against the CEO's automation Chrome fixing every selector it
proved wrong, and one real proof shot. **Stopped mid-way per CTO
instruction (19 Sep, msg 3859781c)** — a real bug came out of the proof
run's own log and outranked finishing it. This report covers all of it:
the flag work, the full live selector-fix findings, the bug the CTO caught,
the fix, and what is still unverified.

## Worktree note

My branch tip was 13 commits behind local `main` (missing the entire
task-6eabea66 base — `tools/flow_shoot.py` didn't exist in my worktree at
all). Fast-forward merged `main` in before reading anything; same issue
task-6eabea66's own report already flagged as a recurring trap.

## Part 1 — `--resolution` and `--force-duration`

- `--resolution {720p,360p}` (default `720p`) on `run`: set in
  `FlowBrowser.set_settings()`, read back in `read_settings()` alongside
  the existing model/mode/aspect/qty checks.
- `--force-duration N` (proof shots only): new `effective_duration(sheet_dur_s,
  force_duration)` helper — overrides the sheet's per-shot duration for
  BOTH the composer's duration setting and `verify_clip()`'s tolerance, so
  the two can never disagree. Logs loudly at the top of the run when active.
- 9 tests (arg parsing incl. rejecting a bad resolution, settings-dict
  read-back match/mismatch/default, verify-tolerance under override).

Commit `b458b2ca`.

## Part 2 — live dry-run, every selector fixed

Polled `http://127.0.0.1:9223/json/version` — already up, CEO already
logged in, «บัญชี» project tab already open. No 45-minute wait needed.

**Everything in `FlowBrowser` was unverified going in** (built blind from
docs in task-6eabea66). Ran `run --only 3 --resolution 360p
--force-duration 4 --credit-cap 0 --dry-run` repeatedly, fixing one broken
selector at a time by reading the live DOM directly through Playwright (no
screenshots, per the brief). **Zero credits spent in this part** — every
fix was validated by re-running the same `--credit-cap 0 --dry-run`
command, which cannot submit.

### Settings panel (`set_settings`/`read_settings`)

The composer's collapsed pill (`aria-label="ทริกเกอร์การตั้งค่า"`) has **no
per-facet aria-labels** — `"Ratio"`, `"Duration"`, `"Resolution"` never
existed anywhere in the DOM; the original guesses always timed out. Every
real facet lives inside the `<flow-prompt-box-settings>` overlay panel that
button opens, as Angular Material `mat-button-toggle` groups (image/video,
เฟรม/องค์ประกอบ, aspect, resolution, duration, quantity), matched by each
option's own visible text. The panel **defaults to the "รูปภาพ" (Image) tab
on open** — "วิดีโอ" must be clicked first or every later facet click hits
the wrong sub-panel.

Read-back had a deeper bug than a wrong selector: **every toggle label
(720p, 360p, x1..x4, every duration, every aspect ratio) is ALWAYS rendered
regardless of which is selected.** The original `"720p" in body` style
check was true whether or not 720p was actually active. The selected
option alone carries `mat-button-toggle-checked` on the
`<mat-button-toggle>` wrapper, one level above the clickable `<button>` —
that class is now the only thing read.

Both opening the panel and switching to the video tab are **racy**
(confirmed empirically — an open that failed once succeeded on retry with
no code change). Both now poll/retry instead of trusting one click+wait.

### Credit estimate (`read_credit_estimate`)

`"การสร้างจะใช้ N เครดิต"` renders **only inside the open settings panel** —
confirmed present in `document.body.innerText` while open, gone the instant
it closes (this is a real instance of the skill's documented "settings
panel is an overlay that text reads miss" trap, now measured precisely:
it's not that the text is unreadable, it's that it doesn't exist in the DOM
at all when closed). `read_credit_estimate()` now reopens the panel fresh
each call and closes it again afterward, matching BANCHI-SHOOT-BRIEF.md's
"read it immediately before Submit."

### Submit button

Real `aria-label` is **`เริ่มสร้าง`** ("Start generating") — never
`"Submit"`.

### Chip attach (`attach_chip`/`chip_count`)

The ingredient picker is **not open by default** — opens via the
composer's own `+` button, `aria-label="เพิ่มองค์ประกอบลงในช่องพรอมต์"`, and
**auto-closes after every attach**, so it must be reopened per handle. Once
open: single-click the matching `.asset-item` row (confirmed class,
matches google-flow-ops' 2026-09-08 note), which opens a preview pane with
its own `เพิ่มไปยังพรอมต์` button — click that to actually attach. The
brief's older "⋮ more options" menu path was **not found live** on this
project; dropped rather than kept as a silently-dead fallback.

A successfully attached chip renders as
`<flow-ingredient-chip><flow-character-ingredient-chip>...` — **not** the
old `span.mention-chip[data-entity-id]` guess (0 matches, always, on this
live DOM). And `flow-ingredient-chip` alone is **page-wide**: every past
generation card in the feed renders its own (19+ matches on this modest
project) — `chip_count()` now scopes to the composer's own
`<flow-ingredient-bar class="prompt-ingredient-bar">`, confirmed to appear
exactly once in the whole page.

### Prompt paste (`paste_prompt`)

Typing character-by-character via `page.keyboard.type()` **mashed the
sheet's blank-line paragraph breaks together with zero separator at all** —
`"...for staircase.In a narrow steep wooden staircase..."`, one run-on
sentence where the sheet has a blank line. `page.keyboard.insert_text()`
(the same CDP `Input.insertText` primitive a real paste uses) reproduces
every paragraph break correctly.

The editor still **re-normalizes the exact newline count** on its own
terms on round-trip — confirmed by diffing character by character: a
single `\n` between two dialogue lines and a blank-line `\n\n` between two
paragraphs both come back as *some* run of newlines, not necessarily the
source's count, but **every character of actual text survives**. New
`normalize_prompt_whitespace()` (collapses `\n+` → `\n`, strips) is now
what the mismatch check compares, replacing a raw-string comparison that
could never pass a correctly-pasted multi-paragraph prompt.

Commit `96519c19` has the full technical detail per-selector; kept above.

## Part 2 result

Dry-run reached: settings confirmed ✓, both chips attached ✓, prompt
verified (content, not raw bytes) ✓, credit estimate read = **4 credits**
for Omni 1.1 Flash / 360p / 4s / 9:16 / x1 / องค์ประกอบ — a new
measurement, not previously in google-flow-ops (which only had 360p/8s=6).
Run correctly stopped at `CAP REACHED: spent=0 + estimate=4 > cap=0`
**before ever reaching Submit.** Zero credits spent in this part.

One self-inflicted false failure along the way: a stray
`.cdk-overlay-backdrop` left open by my own manual credit-balance-reading
script blocked every click for one run attempt (`"...intercepts pointer
events"`). Not a code bug — clicking the backdrop away fixed it. Noted
here so nobody chases it as a real selector problem.

## Part 3 — the proof shot, and the bug the CTO caught

Balance before, read from account menu (`div[aria-label="รายละเอียดบัญชี"]`,
the correct selector — `รายละเอียดบัญชี` = "account details"; nothing
matching "account"/"avatar"/"profile" existed in any aria-label):
**8,552 credits.**

Fired the real command per the brief:
```
tools/flow_shoot.py run --sheet docs/scripts/banchi-ACT1.md \
  --ledger state/banchi/PROOF.tsv --dest /tmp/banchi-proof \
  --only 3 --resolution 360p --force-duration 4 --credit-cap 10
```

**19:03:30** — `attach_chip(@staircase) failed:
TimeoutError('Locator.click: Timeout 2000ms exceeded ... waiting for
get_by_text("เพิ่มไปยังพรอมต์")')`

**19:03:31** — `shot 3: submitted (attempt 1, est 4 credits)`

One second after a logged chip-attach failure, the runner submitted
anyway. Root cause: `_attempt_chip()`'s only signal is "did `chip_count()`
rise since before this handle was attempted" — a heuristic, not proof the
*right total* ended up attached. Nothing re-verified the total count
against what the shot actually needs before the code moved on to
`paste_prompt` → `read_credit_estimate` → `submit`. This is exactly the
failure BANCHI-SHOOT-BRIEF.md itself warns about: *"A missing chip means
the shot generates with no reference and nobody finds out until the
frames are reviewed."*

A stale-ledger symptom compounded the confusion: the row's `note` field is
only ever written on a failure path, so the row that reached `submitted`
still carried `note="chip never attached: @lung_somchai"` — text left over
from an EARLIER, unrelated failed attempt (my own backdrop mishap from
Part 2), not evidence about *this* submission.

**19:11:32** (8 minutes later) — `shot 3: failed — timeout`. The runner's
own `poll_result()` never saw a download button appear and gave up.

### The fix (commit `985a670c`)

1. **Hard gate.** After the per-handle attach loop, re-read the live chip
   count once more and require `live_chip_count == len(shot["chips"])`
   exactly. A mismatch is `needs_model` and the shot is skipped —
   `continue`, never reaching `paste_prompt`/`read_credit_estimate`/`submit`.
   Used the *verified* `chip_count()` (`flow-ingredient-bar
   flow-ingredient-chip`) rather than the `span.mention-chip[data-entity-id]`
   selector named in the CTO's message — that selector is confirmed (Part 2)
   to match zero elements on the live DOM; using it would have made the
   gate permanently trip (every shot `needs_model`, nothing ever fires).
2. **Stale-note fix.** `row["note"] = ""` at the top of every attempt, so a
   row that fails once and later succeeds doesn't keep displaying the old
   failure text next to its new status.
3. **`cmd_run(args, browser_factory=FlowBrowser)`** — the browser is now
   injectable, so a test can exercise the *actual control flow* (proving
   `submit()` itself is never called) rather than just a pure boolean
   helper.

### Tests for the gate

Two new tests use a stub `FlowBrowser` whose `chip_count()` plays back a
scripted call sequence **decoupled from `attach_chip()`** — this is what
lets a test reproduce the live bug precisely: every per-handle "count
increased" check inside `_attempt_chip` can pass (sequence rises 0→1→1→2→2→3)
while the hard gate's own final re-read still comes back wrong (drops to 2
— modelling a transient over-count during polling that reverts by the time
of the authoritative check):

- `test_chip_count_mismatch_blocks_submit` — `submit()` never called,
  `download()` never called, row → `needs_model`, `rc == 1`.
- `test_chip_count_match_reaches_submit` (positive control, same rising
  sequence but the final read holds at 3) — `submit()` **is** called,
  proving the gate doesn't false-block a correct attach.

`pytest tests/test_flow_shoot.py`: **52 passed.**
`tools/check_replay_script.py tools/flow_shoot.py tools/flow_ledger.py`: exit 0.

### Per CTO instruction: did not re-fire

The ledger row is left exactly as the bug produced it —
`state/banchi/PROOF.tsv` shot 3: `status=failed`, `attempts=1`,
`note=timeout` — **not committed** (per-run local state, not a code
artifact; also explicitly requested left as evidence).

### What actually happened to the credits — checked read-only, no re-fire

Balance after, same account-menu read: **8,548 credits.** Delta = **4
credits, exactly matching the read estimate.** So the generation was
genuinely charged and — checked by reading the feed (no click, no
download, no ledger write) — **the clip actually completed**: the most
recent card in the project shows the exact shot-3 prompt text, a `360p`
badge, and a real `download` control, sitting right where our runner's own
8-minute poll gave up and called it a timeout.

This points at a second, real bug I did **not** fix (out of the CTO's
explicit 3-item scope, and the instruction to stop): `poll_result()`'s
completion check and `download()`'s click target both use
`[aria-label="Download"], [aria-label="ดาวน์โหลด"]`, which — checked live,
read-only — **matches zero elements.** The only elements with matching
text are `<mat-icon>download</mat-icon>` (no aria-label of its own,
ligature icon text only) nested in buttons whose actual aria-label is
`"ดาวน์โหลดแบบกลุ่ม"` ("bulk download", a different, multi-select control).
If this is representative, **every real shot the runner ever submits will
time out after 8 minutes even on success**, because it is polling for a
selector that cannot exist. This is the single most important next fix —
flagging it here rather than touching it, per the stop instruction.

## What is still unverified live

- **`poll_result()` / `download()`'s selectors — confirmed wrong** (see
  above). Not fixed this session.
- Whether `find_card_by_dialogue()` / `pull` (never exercised — `run` never
  got that far) work against the real feed.
- Whether the model-select dropdown path (`role=menuitem`, "Omni 1.1
  Flash") is needed in practice — on every live run so far the account
  default was already Omni, so that branch's actual click was never forced
  to fire for real.
- Whether `attach_chip`'s row-click alone (without the confirm button) is
  sometimes sufficient for some asset types — one dry-run observation
  suggested this for `@staircase` but was not conclusively isolated.

## Replay Script: `tools/flow_shoot.py`

## Skill learning

- **WRONG** — `google-flow-ops`'s "Composer settings row — what it shows"
  section describes only the collapsed pill's flattened text
  (`วิดีโอ · 720p · 8 วินาที · 9:16 · x1`) and never documents that this is
  purely display text with no clickable per-facet control on it — every
  actual facet lives one click deeper, inside `<flow-prompt-box-settings>`,
  behind a `วิดีโอ`/`รูปภาพ` tab switch that defaults to the wrong tab.
  Evidence: live DOM dumps in this session, task-a09ed18a. Worth folding
  into the skill so the next runner (or operator) doesn't re-derive this
  by hand.
- **WRONG** — the brief's chip-attach path ("⋮ more options" menu) was
  already superseded once (google-flow-ops 2026-09-08, single-click-row +
  preview-pane button) and this session found **neither of those**
  matches the current "+"-button-opens-a-picker flow. The picker/preview
  mechanic itself is right (single-click row → separate confirm button),
  but the entry point (`เพิ่มองค์ประกอบลงในช่องพรอมต์`) isn't documented
  anywhere yet.
- **MISSING** — nothing in google-flow-ops or BANCHI-SHOOT-BRIEF.md warns
  that a `mat-button-toggle` LABEL being present in the page text is not
  evidence it's *selected* — every option in every toggle group renders
  unconditionally. Anyone reading settings back by text-search alone will
  reproduce this bug.
- **MISSING** — nothing documents that the credit estimate text only
  exists in the DOM while the settings panel is open (not just "hard to
  read," genuinely absent when closed).
- **MISSING** — the submit button's real aria-label (`เริ่มสร้าง`) isn't
  recorded anywhere; every doc that mentions it just says "Submit."
- **MISSING** — the download button's real markup (`<mat-icon>download</mat-icon>`
  with no aria-label of its own, nested under a button whose aria-label is
  actually `ดาวน์โหลดแบบกลุ่ม`) isn't recorded, and this is the live bug
  most likely to burn real credits on a run that then reports `failed`.
- **COSTLY** — figuring out the settings panel's true structure (Image tab
  default, video-tab switch race, checked-class vs. label-presence) took
  the most live back-and-forth of this session — each wrong guess had to
  be disproven by dumping the actual DOM rather than trusting the brief's
  prose description, since the prose was written from an earlier UI state.
- **COSTLY** — my own manual DOM-probing script left a `cdk-overlay-backdrop`
  open, which then made the NEXT real `run` attempt fail with what looked
  like a fresh selector bug (`"...intercepts pointer events"`) but was
  actually self-inflicted. Anyone driving this UI by hand between runner
  invocations needs to explicitly close every overlay (`Escape`, or click
  the backdrop) before handing control back to the script.

## Files Changed

- `tools/flow_shoot.py` — `--resolution`/`--force-duration` flags,
  `effective_duration()`, `normalize_prompt_whitespace()`, rewritten
  `FlowBrowser.set_settings`/`read_settings`/`read_credit_estimate`/
  `submit`/`attach_chip`/`chip_count`/`paste_prompt` against the live DOM,
  the chip-count hard gate, `cmd_run(browser_factory=...)`.
- `tests/test_flow_shoot.py` — 15 new tests across the three commits (arg
  parsing, settings-dict read-back against a fake checked-class panel,
  verify-tolerance under override, prompt-whitespace normalization, the
  two chip-count-gate control-flow tests).
- `docs/ops/flow-runner-USAGE.md` — documented the two new flags.

## Commits

- `b458b2ca` — flow_shoot: add --resolution and --force-duration to run
- `96519c19` — flow_shoot: fix every FlowBrowser selector against the live UI
- `985a670c` — flow_shoot: hard-gate chip count before submit (CTO)

## Tests

- ran: `pytest tests/test_flow_shoot.py`
- passed: 52
- failed: 0
- skipped: 0
- ran: `python3 tools/check_replay_script.py tools/flow_shoot.py tools/flow_ledger.py`
- result: exit 0 (`ok` on both files)

## Issues / Blockers

- **`poll_result()`/`download()` selectors are confirmed wrong** (0 DOM
  matches, live) — every real shot will time out after 8 minutes even on
  success, as this run's own proof shot did. Highest-priority next fix;
  intentionally left untouched per the CTO's explicit 3-item scope and
  stop instruction.
- The proof shot's ledger row is left as `failed`/timeout, per CTO
  instruction — the underlying clip did generate successfully (confirmed
  read-only: 360p badge, matching prompt, download control visible in the
  feed) and 4 credits were spent (balance 8,552 → 8,548, confirmed against
  the read estimate). Retrieving it needs `pull` (or a fixed `poll_result`)
  and is the CTO's call, not re-fired here.

## Notes for Reviewer

- Credit balance: **before 8,552 → after 8,548 (delta 4)**, matching the
  live-read estimate for Omni 1.1 Flash / 360p / 4s exactly.
- `state/banchi/PROOF.tsv` and `state/banchi/flow_shoot.log` are untracked,
  intentionally not committed (per-run local state / evidence, per CTO).
- If the CTO wants the actual proof clip retrieved next, `pull` should
  work today (download-only, doesn't touch settings/chips/submit) — but
  its own download-click path shares the same broken selector as
  `poll_result`/`download()`, so it likely needs that fix first.
