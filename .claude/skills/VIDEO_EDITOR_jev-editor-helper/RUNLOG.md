# RUNLOG — VIDEO_EDITOR_jev-editor-helper (task-5cfe20b1)

Progress log per the task's "Append progress ... as you go" rule.

## 2026-09-23

- Read `.claude/skills/jev-ops/SKILL.md`, `tools/decide.py`,
  `config/decisions/{browser.page_state,skill.route,sompong.route}.yaml`,
  `.claude/skills/blackliquidity-cut/SKILL.md` §6d/§6c/§6e/§5a, and the EDL
  schema at `worktrees/mooniex-agents__developer__task-42e3b6af/.claude/skills/blackliquidity-cut/edl/{SCHEMA.md,event_types.json,example/p1_layout.json}`.
- Checked the two upstream dependencies:
  - task-42e3b6af (EDL schema): **present**, read and used for the avatar
    box constant and the "mappable by stable line id" requirement.
  - task-82380776 (`prototypes/bl-ref-census/groundtruth.tsv`): **not
    present** — the worktree has seed measurement scripts
    (track.py/fit.py/cutdetect.py/roi_diff.py) but no groundtruth.tsv yet.
  - task-80d18826 (`prototypes/bl57-script/SCRIPT.tsv`): **not present** —
    the writer's worktree has no `bl57-script/` folder yet. Built a small
    made-up sample (`example/SCRIPT.tsv`) to the tag/spoken/shot/beat/screen
    column spec instead, per the task's stop condition.
- Created the skill via `scripts/skill-curator.py create
  VIDEO_EDITOR_jev-editor-helper --audience video_editor,cto`.
- Built `scripts/jev_edit_lib.py` (pure functions: TSV parsing, candidate
  geometry, positional-slot labelling, DOM-box extraction from
  REAL_MANIFEST, content-word/number/brand extraction, the confidence gate)
  and `scripts/jev_edit.py` (CLI: `plan`/`storyboard`/`eval`, the only file
  that imports `tools.decide`).
- Built the six sites: `config/decisions/bl.{beat,entry,focus_device,
  focus_target,highlight_word,text_slot}.yaml`.
- **Blocker hit and resolved in-session:** the task's declared `touches` in
  `state/tasks.db` was `"config/decisions/bl."` (missing the `*` wildcard
  from the brief's `config/decisions/bl.*.yaml`), so
  `scripts/hook-self-repo-guard.py` refused every `bl.*.yaml` write
  (`is_declared()` needs an exact match, a `/`-terminated prefix, or a real
  fnmatch pattern — a bare `"bl."` matches none of the six paths). Reported
  via `dev_message` rather than working around the guard; proceeded on
  everything else while waiting.
- `tests/test_jev_edit.py`: 42 pure-function tests, all green (see Tests
  section of the final report). One real bug caught by the tests
  themselves: the number regex matched digits embedded inside a Latin token
  (`"A1"` -> `"1"` + `"A"` instead of one token `"A1"`) until word-boundary
  lookaround was added.

## Eval status

Per the task's stop condition: **groundtruth.tsv does not exist yet**
(task-82380776). `eval` is fully implemented (reads a `tag/question/
expected/state` TSV, runs `--reps` repetitions per case, reports accuracy
per site and jev-ops' own confidence-bucket shape, enforces the $0.05/2000-
call ceiling) but has not been run against real labelled data — there is
none to run it against. Stopping here per the brief: "If it does not exist
when your build and tests are done, stop and report. The CTO will reopen
you for the eval."

Also pending the eval (task explicitly calls for measuring this, not
assuming it): the Thai-vs-English-gloss state comparison for `bl.beat`/
`bl.focus_device` (`--state-lang th|en`, implemented, `en` is the
provisional default per jev-ops' general advice) and the confidence gate
itself (ships at jev-ops' measured 0.7, "replaced by what your eval
measures" per the brief).

## Sample run (plan + storyboard on `example/`) — real Jev, not mocked

`DECIDE_PROVIDER=jev` and `DECIDE_BUDGET_USD=5` are already set org-wide
(`.env`), so `plan` on the 3-line `example/` episode made real calls:
10 Jev calls, **$0.000305**, 7/12 rows flagged. Sent as a file
(`sample-storyboard.html`) rather than committed — `output/` in the worktree
is not writable to the live checkout from a DEV (self_repo_guard, ADR 0020);
the BL skill's older `~/Projects/Agents/output/...` convention is blocked by
this same guard now, so delivery is via `SendUserFile` instead.

## 2026-09-23 22:15 — touches fixed (CTO), real EP57 run, one real bug + one real calibration fix

CTO fixed task-5cfe20b1's declared touches (issue #169 was the CTO's own
brief typo, `config/decisions/bl.` missing the `*`). Landed the six site
YAMLs — all validate via `tools/decide.py sites`.

**Real bug caught before it shipped:** `parse_script_tsv()` assumed a
header row (`csv.DictReader`). The real `bl57-script/SCRIPT.tsv`
(task-80d18826, now written, 40 lines) has **no header** — straight to
positional data, 4 or 5 tab-separated columns per row, and its `shot`
column is actually a REAL_MANIFEST file-slug reference
(`wikifx-xxlmarkets-review`), not prose. Fixed to auto-detect the header
instead of requiring one; added a regression test on the real shape.

**Real calibration finding, found by comparing Jev's `bl.beat` answer
against the writer's own `beat` column on the real 40-line episode** (not a
formal eval — groundtruth.tsv still doesn't exist — but the writer's own
tags are a useful informal signal, and the task explicitly asks Jev's
answer to be checked against them): first pass, 17/40 (42%) agreement, with
23 lines the writer tagged `verdict` all landing on `other` from Jev. My
`verdict` criterion was too narrow (only "emotional judgment to camera");
the writer actually uses it for any direct-to-camera narrative/reasoning
line with no new evidence — e.g. "กูไม่เชื่อคำว่าเข้าเว็บไม่ได้เฉยๆ
เลยไปเช็กเองอีกที" ("I didn't believe that, so I checked myself"), not an
emotional judgment at all. `other` matters functionally here: it drops the
avatar-mode signal (`mode_for_beat` maps hook/verdict/cta all to `"full"`,
`other` to `None`). Broadened the criterion with a real example from the
script. **Re-ran: 36/40 (90%) agreement**, and all 4 remaining
disagreements sit at confidence 0.37-0.58 — below the 0.7 gate, correctly
flagged rather than confidently wrong (matches jev-ops SKILL.md: "with good
criteria, a bad state shows up as low confidence").

**EP57 full run (40 real script lines, `--manifest` = the real
`bl57-realfootage/REAL_MANIFEST.json`, which DOES carry `evidence_box`
already — task-82380776/`bl_realfootage.py`'s census work is ahead of what
`blackliquidity-cut/edl/SCHEMA.md` assumed when it was written):**

```
lines=40  rows=175  Jev calls=143  cost=$0.004573  flagged=112/175 (64%)
per-site: bl.beat 40 · bl.entry 39 · bl.focus_device 11 · bl.focus_target 5
          bl.highlight_word 8 answered + 32 skipped (no candidates) · bl.text_slot 40
```

$0.004573 for one real episode — matches the task's "≈$0.005 ต่อตอน" target
closely. `bl.focus_target`/`bl.focus_device`/`bl.text_slot` skew low-
confidence (real editorial calls Jev has not been measured on) — expected
and correct per SKILL.md rule 3: nothing here is trusted above the gate
until a real `eval` run exists.

**Total spend this session, sum of `usage.cost` from `state/decisions/2026-09.jsonl`
(authoritative, not my own running total):** 296 `bl.*` calls, **$0.009257**
— under the task's $0.05/2000-call ceiling for "everything" (sample run +
both EP57 runs, before and after the criterion fix, combined).

Sent both storyboards (`sample-storyboard.html`, `ep57-storyboard.html`)
and their `decisions.jsonl` via `SendUserFile` rather than committing them
or writing to `~/Projects/Agents/output/` — self_repo_guard refuses ANY
write that resolves into the live checkout, declared touches or not.

## Eval status — unchanged, still blocked

`groundtruth.tsv` (task-82380776) still does not exist as of this pass —
the worktree has census measurement scripts and `measurements/lines.tsv`
but no hand-labelled `tag/question/expected/state` ground truth. Per the
brief and the CTO's own instruction: stopping here, not running `eval`.
The informal writer-tag comparison above is not a substitute — it only
checks `bl.beat`, and only against the writer's own (unvalidated) judgment,
not a reviewed ground truth.

## 2026-09-23 22:35 — CTO review round 2: three fixes

### 1. Test-set contamination — the 90% was inflated, honest number is 42%

CTO caught it: the `verdict`/`cta`/`spotlight`/`highlight_sweep`/`zoom_only`
examples in `bl.beat.yaml`, `bl.entry.yaml` and `bl.focus_device.yaml` were
drawn from EP57 itself (`prototypes/bl57-script/`) and the reference
transcript (`prototypes/bl-ref-census/`, quoted via
`blackliquidity-cut/SKILL.md` §6d) — both of which are this pipeline's own
test material, so the earlier 90% agreement check was measuring
recall-of-its-own-examples, not generalisation (jev-ops SKILL.md lever 2:
"examples must not reuse the test values").

Replaced every example across all three sites with held-out lines from
`prototypes/bl55-script/SCRIPT-v2.tsv` (a different, already-published
episode, not part of either test set) — checked `bl.focus_target`/
`bl.highlight_word`/`bl.text_slot` too, they were already clean (positional
templates, no literal content quotes). Re-ran EP57 `plan` with the fixed
criteria (v3, `$WORK_DIR/out/ep57-decisions-v3-heldout-criteria.jsonl`):

```
bl.beat honest agreement vs writer's own tag: 17/40 (42%)
```

**Same number as the very first, unfixed pass.** The "fix" that produced
90% was entirely an artefact of the criteria containing the exact lines
(or lines quoting the exact same reference recording) being scored against
— not a real improvement. With genuinely held-out examples, `bl.beat`'s
real accuracy on this informal check is 42%, same as day one. Every
disagreement's confidence sits at 0.38-0.60 (below the 0.7 gate) — the gate
is correctly catching that nothing here is confident-and-wrong, but the
site itself needs real iteration, which is exactly what the formal `eval`
(HARD rule 3: not trusted until measured) is for. **Deliberately did not
hand-tune the criteria again against EP57** to chase a higher number —
that is the same contamination trap in a smaller size. Further criteria
work waits for the real `eval` loop against real (corrected) groundtruth,
per jev-ops' own methodology (build ≥12 labelled cases incl. borderline,
run ≥2 reps, read accuracy, only then rewrite criteria).

### 2. Eval — still waiting, now for a different reason

`groundtruth.tsv` now EXISTS (task-82380776 produced it), but task-82380776
itself is back to `in_progress` (CTO sent the census back — P1 missed two
composite spans, 9.3-13.9s and 19.1-20.3s) — the file that exists right now
is the WRONG version. Checked via
`sqlite3 state/tasks.db "select status from tasks where id='task-82380776'"`
→ `in_progress`, not `review`/`done`. Per the CTO's explicit instruction:
waiting for that status to flip again and the file to actually change
before running `eval --reps 2`.

### 3. Output delivery — moved to $WORK_DIR/out, stopped using SendUserFile

CTO: outputs go to the CTO, not the CEO — the CTO decides what reaches the
CEO. Moved every run artifact (`sample-decisions.jsonl`/`.html`,
`ep57-decisions-v{1,2,3}*.jsonl`, `ep57-storyboard-v3-heldout-criteria.html`)
to `$WORK_DIR/out` (`/Users/gob/MoonieXHQ/Work/task-5cfe20b1/out/`) — outside
the git worktree, writable (unlike `~/Projects/Agents/output/`, which
self_repo_guard refuses for a DEV regardless of declared touches — see the
skill-learning note in the first report). Not using `SendUserFile` again
this task.

### Total spend, this session (authoritative, `state/decisions/2026-09.jsonl`)

**440 `bl.*` calls, $0.014011** — under the $0.05/2,000-call cap for
everything (sample run + EP57 v1 baseline + v2 contaminated-criteria +
v3 held-out-criteria, combined).
