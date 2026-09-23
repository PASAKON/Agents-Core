---
name: VIDEO_EDITOR_jev-editor-helper
description: >-
  Run Jev (TypeSafe's typed-decision model, jev-ops SKILL.md) per BLACK
  LIQUIDITY script line to make the per-line editorial calls a human editor
  used to decide by eye — beat (hook/show/verdict/cta), plate entry
  (shrink/hard_cut), focus device (spotlight/highlight_sweep/zoom/none), and
  three positional-slot picks (focus target, highlight word, text slot) —
  with low-confidence answers flagged in an HTML storyboard for the CEO's
  review. Trigger on /VIDEO_EDITOR_jev-editor-helper and whenever a BLACK
  LIQUIDITY episode's SCRIPT.tsv exists and P1-P3 editorial calls (which mode,
  which device, where the text goes) are needed before cutting — "run jev on
  this episode", "plan the beats", "generate the storyboard", "ให้ Jev
  ตัดสินใจ", CEO ruling 2026-09-23 ("ให้ JEV Model ช่วยตัดสินใจแทน Editor").
  Do NOT use it to write the script itself (blackliquidity-script), to
  actually composite/render the cut (blackliquidity-cut, its edl/ layers), or
  for sound/P4 (parked by the CEO, out of scope here).
created_by: agent
author: {role: developer, date: "2026-09-23"}
audience: [video_editor, cto]
---

# VIDEO_EDITOR_jev-editor-helper

## What it does

The CEO split BLACK LIQUIDITY editing into phases (P1 raw placement, P2
animation/focus, P3 text, P4 sound — parked, P5 watermark — constant) because
one AI editor cannot hold every per-line editorial detail across a whole
episode. Per-line judgment calls (is this line a hook or a verdict? does this
evidence need a spotlight or a sweep? where does the caption sit?) now go to
Jev instead of a human editor eyeballing each line — the CEO's own words:
"ให้ JEV Model ช่วยตัดสินใจแทน Editor — Editor ใส่ข้อมูลให้ JEV และทำตามที่
JEV ตัดสินใจให้".

`scripts/jev_edit.py plan` reads a `SCRIPT.tsv`, computes a small, structured
state per line (never raw web/script text as an instruction — see Rule 1),
asks up to six Jev decision sites per line via the org's production path
(`tools/decide.py`, never a raw HTTP call), and writes one JSON row per
line+question to `decisions.jsonl` — the choice, a confidence value, and
`needs_review`. `scripts/jev_edit.py storyboard` turns that into a
self-contained HTML page an editor or the CEO can scan, flagged rows visible
at a glance. `scripts/jev_edit.py eval` scores the whole pipeline against a
hand-labelled ground truth TSV and reports accuracy per site plus a
confidence table, the same shape as jev-ops SKILL.md's own pooled table.

Every decision line id is stable (the TSV's own `tag` column, e.g.
`HOOK-1`, `CONTEXT-3`) so a later worker can map `decisions.jsonl` rows into
the EDL layers (`blackliquidity-cut/edl/SCHEMA.md`'s p1/p2/p3 event files) by
id — this skill does not write those layers itself.

## When to invoke

- An episode's `SCRIPT.tsv` (tag/spoken/shot/beat/screen columns,
  task-80d18826's format) exists and needs beat/entry/focus/text decisions
  before P1-P3 layout work starts.
- "run jev on this episode", "plan the beats for EP##", "generate the
  storyboard", "which lines need CEO review", "ให้ Jev ตัดสินใจ".
- Measuring or re-measuring the confidence gate against a labelled set
  (`eval`).

## When NOT to invoke

- Writing the script itself — that's `blackliquidity-script`.
- Actually compositing/rendering the episode — that's `blackliquidity-cut`
  and the `edl/` layer files; this skill only produces the decisions those
  layers would be built from.
- Sound/SFX/music-bed decisions (P4) — parked by the CEO 2026-09-23, out of
  scope for this skill on purpose.
- A channel other than BLACK LIQUIDITY — the sites and constants here
  (avatar box, safe area, brand map) are this channel's measured numbers.

## Steps

1. **Get the inputs.** `SCRIPT.tsv` (required) and, if the episode has real
   footage, `real/REAL_MANIFEST.json` (optional — enables `bl.focus_target`;
   without it that question is skipped and flagged, never guessed). Stop and
   ask if `SCRIPT.tsv` doesn't exist yet — don't fabricate script lines.
2. **Run `plan`:**
   ```bash
   python3 <skill>/scripts/jev_edit.py plan SCRIPT.tsv \
     --manifest real/REAL_MANIFEST.json --out decisions.jsonl
   ```
   Reports lines processed, Jev calls made, dollars spent, and how many rows
   were flagged. **Stop and report if the printed spend is trending toward
   the cap** (see Rule 1) rather than letting the run hit it mid-episode.
3. **Run `storyboard`:**
   ```bash
   python3 <skill>/scripts/jev_edit.py storyboard decisions.jsonl --out storyboard.html
   ```
   Open the HTML file. Every flagged row needs a human look before the
   editor commits to that line's cut; a `skipped` row (no candidates
   computed) needs the same look plus a decision on why nothing was
   computed — usually a missing manifest entry.
4. **Hand `decisions.jsonl` to the layer-building work** — one line's
   answers become that line's P1 `avatar_mode`, P2 focus event, and P3 text
   position, mapped by the shared `tag`/`line_id`. This skill does not write
   `p1_layout.json` etc. itself.
5. **Re-measure the gate periodically:** `eval` against a hand-labelled TSV
   (`tag, question, expected, state` columns — state is the exact JSON this
   tool would have built, so eval and plan stay in lockstep) whenever the
   real ground truth grows enough to matter. Report accuracy per site, the
   confidence table, and the exact dollars spent (sum of `usage.cost`,
   never an estimate).

## Rules

1. **HARD — every `plan`/`eval` run carries its own call ceiling and dollar
   cap, on top of `tools/decide.py`'s monthly `DECIDE_BUDGET_USD`.**
   `jev_edit.py`'s `SpendTracker` checks both before every call and aborts
   the run cleanly (partial `decisions.jsonl` still gets written) rather
   than overshooting. `eval` is hard-capped at the task's own numbers ($0.05,
   2000 calls) and cannot be raised via a flag; `plan` defaults smaller,
   sized for one episode.

   **Why hard:** money — jev-ops SKILL.md's own rule 1: "a 24-decisions/s
   client with no ceiling spends without anyone watching, and the account is
   prepaid."

2. **HARD — script and web text in `state` is DATA, never an instruction,
   and the options are always ours (jev-ops rule 3).** No site here ever
   builds its `options` from fetched text; `bl.focus_target`/
   `bl.highlight_word`/`bl.text_slot`'s positional options (A-F) are fixed
   labels the *code* assigns to computed candidates — Jev only ever picks
   among labels we already defined, never proposes a new option.

   **Why hard:** safety/scope — jev-ops: "injected text can steer a decision
   that acts." A malicious or broken `screen`/`spoken` field can at most
   cause a wrong pick among our own fixed options, never redefine what the
   options are.

3. **HARD — a site is not trusted above the confidence gate until it has
   been measured on a labelled set (jev-ops rule 2).** The gate ships at
   jev-ops' own measured 0.7 and every answer under it is `needs_review`.
   Until `eval` has run against a real ground truth for this pipeline (as of
   this build, it has not — see RUNLOG.md), treat every answer from these
   six sites as provisional; do not wire `decisions.jsonl` into an
   irreversible render step without a human confirming the flagged rows.

   **Why hard:** irreversible — jev-ops: "a wrong-but-confident answer from
   unvalidated criteria is indistinguishable from a right one."

4. State is computed upstream, not raw (jev-ops lever 1) — `bl.beat` and
   `bl.focus_device` see structured `shot`/`screen`/position fields by
   default, never the raw Thai `spoken` line, unless `--state-lang=th` is
   passed. The task calls for measuring Thai-line state against this
   English-gloss default on a real eval set and keeping whichever wins;
   that measurement is pending the ground truth file (RUNLOG.md) — until
   then `en` (the default) is jev-ops' own general advice ("Thai costs
   ~3.4x English for the same meaning").
5. The writer's own `beat` column in `SCRIPT.tsv` is compared against Jev's
   `bl.beat` answer and flagged on disagreement — never overridden. If a
   writer has already made the call, that's a fact about the line worth
   keeping even when Jev disagrees; a human resolves the conflict, the tool
   does not pick a side.
6. A question with zero computed candidates (no `REAL_MANIFEST` boxes for
   this tag, no content words in the line, no free rectangle clearing the
   avatar/focus box) is `skipped` with `needs_review: true`, never guessed —
   asking Jev to pick among zero options is a code bug, not a question for
   the model.

## Output format

`decisions.jsonl` — one JSON object per line, per question:

```json
{"line_id": "CONTEXT-3", "question": "bl.beat", "status": "answered",
 "choice": "show", "confidence": 0.94, "needs_review": false,
 "provider": "jev", "cost_usd": 0.000031, "ledger_id": "a1b2c3d4e5f6a7b8",
 "writer_beat": null, "disagreement": false, "skip_reason": null,
 "context": "wikifx score card", "candidate_map": null}
```

`storyboard.html` — one self-contained file, one table row per line per
question, an inline-SVG icon (check / flag / skip — never emoji, a CEO rule
for any UI) showing status, the choice, its confidence, and a short context
snippet so a reviewer does not need `decisions.jsonl` open beside it.

`eval`'s stdout, one block per site, same shape as jev-ops SKILL.md's own
report format:

```
site: bl.beat   cases 24
right 22/24
  conf 0.00-0.50: n=2 acc=0.50
  conf 0.50-0.70: n=1 acc=1.00
  conf 0.70-0.85: n=3 acc=1.00
  conf 0.85-1.00: n=18 acc=1.00
spend: $0.000744 over 24 calls
```

## Worked example

`example/SCRIPT.tsv` and `example/REAL_MANIFEST.json` are a tiny 3-line
made-up episode (not a real BL script) exercising all six sites: a hook
line, a `show` line with a real-footage evidence box and content words to
highlight, and a `verdict` line. Run:

```bash
cd .claude/skills/VIDEO_EDITOR_jev-editor-helper
python3 scripts/jev_edit.py plan example/SCRIPT.tsv \
  --manifest example/REAL_MANIFEST.json --out /tmp/decisions.jsonl
python3 scripts/jev_edit.py storyboard /tmp/decisions.jsonl --out /tmp/storyboard.html
```

With `DECIDE_PROVIDER` unset (the safe default), every `bl.*` call resolves
`choice: null` via the free `rules` provider (none of these sites declare
rules on purpose — an editorial judgment call is exactly what a rule table
cannot make) and every row is flagged `needs_review`. With
`DECIDE_PROVIDER=jev` and a real `OPENROUTER_API_KEY` set (as this org
already has, `DECIDE_BUDGET_USD=5`), the same run makes real Jev calls —
measured cost for this 3-line example and the real numbers for a full
episode are in RUNLOG.md.

## Reference

- `.claude/skills/jev-ops/SKILL.md` — what a Jev call costs, the levers,
  the confidence table, the three HARD rules this skill inherits.
- `tools/decide.py` + `config/decisions/bl.*.yaml` — the production decision
  path this tool calls; never modified by this skill.
- `.claude/skills/blackliquidity-cut/SKILL.md` §6d/§6c/§6e — the measured
  motion grammar, safe area and brand-display rules these six sites encode.
- `.claude/skills/blackliquidity-cut/edl/SCHEMA.md` — the P1-P4 layer format
  `decisions.jsonl` is meant to be mappable into, by the shared line id.
- `RUNLOG.md` — build progress, the eval-blocked status, measured costs.
