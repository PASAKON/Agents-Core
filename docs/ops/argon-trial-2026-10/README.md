# Gemini 4 Argon trial on real jobs (2026-10-13/14)

The CEO ordered this on 14 Oct at about 01:50 Thai time, relayed by SomPong: "ตัวนี้เก่งเทียบเท่ากับ Sonnet 5.5 เลยหรืออาจจะเก่งกว่า ให้ทดสอบจริงได้เลยกับงานจริง" (this one may match Sonnet 5.5 or beat it; test it on real work). The order came through CONTABO CTO #e106b78b, and CTO cto-d1a121af ran the trial on Contabo.
He narrowed it at about 03:40: use real queued jobs only, keep the output and merge it through the normal gate. Where a blind Sonnet duplicate would waste quota, run Argon alone and score it by the reviewer's pass/redo. Results: `RESULTS.md`.

## Runners
- **Argon**: `agy -p <brief> --model gemini-4-argon-high --mode accept-edits --add-dir <worktree> --output-format json`
  (agy 1.3.4). File edits only, with no shell. It bills the agy `gemini-5h` / `gemini-weekly` buckets, measured with `agy -p /usage`
  before and after each run.
- **Sonnet**: `claude -p --model claude-sonnet-5-5 --effort high`, tools Read/Edit/Write/Glob/Grep only, no MCP,
  project hooks off (`--setting-sources user`). It uses the same tools as Argon, so the comparison is fair.
- Both get the same brief plus the same contract (`jobs.py` CONTRACT): edit in place, write REPORT.md, run nothing.

## Jobs (`jobs.py`)
Nine real jobs from the week's queue:
- five developer S/M jobs: GitHub issues Console#11, Console#27, ClaudeFlow#213 and ClaudeFlow#227, plus the comment-only checker from LungNote f2209b5b item 1;
- three Thai-to-English translations from LungNote f2209b5b items 4–5;
- one shell-free analysis: the batch plan for item 5.
Jobs D2–D5 ran on both runners. D1, T1–T3 and A1 ran on Argon alone, after the 03:40 order.

## Pipeline
1. `run.py --job J --runner argon|sonnet` runs in a clean worktree reset to the repo's recorded base (`bases.json`).
   It saves the diff, REPORT.md, minutes, tokens and quota meters. It is refused while `MemAvailable` < 1 GB.
   `--from-run` + `--extra` start a redo round from an earlier output and add the reviewer's feedback.
2. `test.py` applies the diff to a separate test worktree and runs the job's checks. These are the repo's tests and greps; for D1 they also include
   `hidden_d1.py`; for translations, `checks.md_check` (line count, untouched non-Thai lines, Markdown structure, Thai left).
3. `judge.py` (paired jobs) has a blind Opus 5.5 judge compare the two outputs, labelled A/B by a seeded coin (key in
   `judge/key.json`): USABLE 2 / CORRECT 1 / WRONG 0, plus a 0–10 score and the better one.
   Argon-only jobs get the reviewer's verdict in `review/<job>.json`.
4. Only one output per job lands, after the normal merge gate (CTO_Gate_MergeChecklist, with the §2b security pass on
   auth code). `landing.json` records which one and its sha.
5. `score.py` gives the tables in RESULTS.md. `fit.py --write` writes one `runner_fit` record per runner per job through
   `tools/runner_fit.py`, with first_pass, redo count, minutes and the bucket move.

`queue.sh`, `post*.sh` and `redo*.sh` are the shell loops that ran these steps one worker at a time. The data
(diffs, reports, verdicts) stays on Contabo in `state/argon-trial-2026-10/`. It is not committed: the repo is public.
