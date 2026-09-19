# Flow operator — design for zero-token shooting (CEO ask, 2026-09-19)

**The ask:** usage is at 95 % of the weekly limit. Design the operator *before*
shooting more, so it is as cheap as possible, finishes the work, and forgets
nothing.

**The one-line answer:** stop paying a model to click. Port the pattern the org
already runs for Higgsfield — `scripts/higgsfield/gen_loop.py`, "STANDALONE, no
Claude in the loop, zero token cost at runtime" — to Google Flow. A model is
consulted only when the script hits something it cannot decide.

## Where the tokens actually go (measured, this week)

| fact | source |
|---|---|
| `claude-in-chrome` MCP = **67 %** of 7-day usage; `/browser-operator` 26 % | CEO's usage panel, 19 Sep |
| 64 % of sessions ran above 150 k context | same |
| A browser_operator shot today: 30–60 MCP calls, up to 6 screenshots, ~25 min wall-clock incl. download and rename | task-083d64b5 / 0e2db53c panes |
| Screenshots never leave a context: every later turn re-sends every earlier image | IRON-RULES §42 |
| Worker "replay script" delivered today = 128 lines of prose notes, not code | cc16c251 — Gate 8 satisfied by writing notes again |

The cost is structural: each shot's screenshots stay in the worker's context, so
the 12th shot pays for the first 11. No brief tightening fixes that. Only taking
the model out of the per-shot loop does.

## The design

```
 shot sheet (banchi-ACTn.md, built from .data.py)      ← the only prompt source
        │
        ▼
 ledger  state/banchi/shots.tsv   one row per shot, the runner's memory
        │   shot · act · status · flow_clip_id · file · sha256 · dur · attempts · note
        ▼
 runner  tools/flow_shoot.py  (Playwright over CDP, port 9222, dedicated Chrome profile)
        │   for each row with status ∉ {verified}:
        │     set model/mode/aspect/qty → attach chips by handle (poll DOM for the
        │     mention-chip, retry ≤ 5) → paste prompt → assert innerText == sheet
        │     → read live credit estimate → submit → poll the card until the
        │     download button exists → page.expect_download() → rename shot-NN.mp4
        │     → ffprobe duration == sheet ±0.6 s → sha256 → row = verified
        │   on refusal card: re-fire the identical prompt ONCE (refunded);
        │     second refusal → row = refused, note = card text verbatim; continue
        │   on chip-attach failure ×5, duration mismatch, unknown dialog:
        │     row = needs_model, note = what was seen; continue
        ▼
 exception worker (only if any needs_model rows exist): a FRESH small-context
        Claude task that reads the ledger rows + note, fixes the one thing
        (rewrites a line / attaches by hand / reads a new dialog), sets the row
        back to todo, exits. Never loops over shots.
        ▼
 filing  after each act: assemble_act.py (refuses on a missing shot), clip_review.py,
        copy to the synced Drive folder All Scene/ACT<n>/, verify by size from
        Drive's listing, append logs.txt, delete local — the CEO's loop, scripted.
```

**Why this forgets nothing:** the ledger, not a context window, is the memory.
A runner killed mid-act restarts and continues from the first non-verified row.
A shot is never re-fired once verified; a shot is never silently skipped because
the ledger is generated from the sheet, so every shot has a row before the first
click.

**Why this costs ~0 tokens per shot:** the runner is Python. The only model
spend is (a) building it once, (b) the exception worker, which sees one row and
one note, not 40 screenshots.

## What exists already vs what must be built

| piece | state |
|---|---|
| Playwright-over-CDP runner with dedicated Chrome profile, resumable index, download, Drive upload | **exists** — `scripts/higgsfield/gen_loop.py` (386 lines) + `launch-chrome-debug.sh` |
| Shot sheets as the single prompt source, per-shot duration, chips in attach order | **exists** — `tools/build_shotsheet.py` |
| Verify + assemble | **exists** — `tools/clip_review.py`, `tools/assemble_act.py` |
| Flow click path (settings, `⋮ → เพิ่มไปยังพรอมต์`, first-keystroke drop, chip count, download button, zip) | **known, written down** — `docs/scripts/BANCHI-SHOOT-BRIEF.md`, `google-flow-ops` |
| Flow-specific runner | **to build** — port gen_loop.py's skeleton; Flow selectors from the brief |
| Ledger format + generator from the sheet | **to build** — small |
| Exception worker brief | **to write** — one page |

Build cost: **one developer task, model_hint=claude** (cheap misses are expensive
here), plus **one real shot** to prove the loop end-to-end (20 credits, 720p).
Estimate, labelled as such: a single session. After that, the remaining 139
shots of «บัญชี» are a script run, not 139 model conversations.

## What needs the CEO, and only the CEO

1. **One login.** The runner drives a *dedicated* Chrome profile
   (`~/.flow-automation/chrome-profile`), exactly as Higgsfield's does, so it
   never touches the CEO's main Chrome. Google login into that profile is the
   CEO's action; the org never handles credentials. Once.
2. **Go/no-go on the build** (one developer task) before any more operator
   shooting. Shooting the remaining 139 shots with browser_operators at today's
   rate is the thing the usage panel is showing.

## Risks, stated plainly

- Flow's chip insertion was measured "about once in fifteen attempts" on one
  run and "without difficulty" on another. A script polls the DOM and retries;
  it does not get tired or guess. If it still fails, that shot lands in
  `needs_model`, and the run continues — it does not stall.
- Google may change selectors. The runner asserts every step by reading the
  DOM back (the brief already requires this of humans); a selector change fails
  loudly at the assert, not silently at review.
- Policy refusals stay stochastic. The runner's rule is the skill's rule:
  re-fire the identical prompt once, then hand the row to the exception worker.

## Rules this design enforces that a brief could not

- A "replay script" that is prose is refused by `cto-merge-checklist` Gate 8.
  This design makes the script the *product*, so there is nothing to satisfy
  with notes.
- IRON-RULES §42: no browser loops in a model's context. The loop is Python.
- The CEO's download → verify → delete loop is a function, not a memory.
