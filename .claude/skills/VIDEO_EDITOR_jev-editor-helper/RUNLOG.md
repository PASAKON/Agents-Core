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

## Sample run (plan + storyboard on `example/`)

See the final report for the exact measured cost and call count of the
3-line worked example (`example/SCRIPT.tsv` + `example/REAL_MANIFEST.json`)
run with `DECIDE_PROVIDER=jev` (already enabled org-wide,
`DECIDE_BUDGET_USD=5`) — the org's real per-episode target is documented in
the task brief as "≈$0.005 ต่อตอน"; this sample is a fraction of one
episode's worth of lines, run to prove the pipeline actually calls Jev and
produces a working storyboard, not to establish the per-episode figure
(that needs a real `SCRIPT.tsv`, still pending task-80d18826).
