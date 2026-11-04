# Claude-out fallback: a Project Head's letters go to its AGY brain

Task task-88615f9e (re-filed from task-635a4385). CEO 4 Nov 2026, Q-20261104-0251-39de:
"คงเดิม (Opus) ทำแค่ AGY ทำต่อ" — C-levels stay as they are; only the PH fallback is built.

## What it does

When the newest `claude` row of `state/reports/quota-history.jsonl` shows `daily_remaining` or
`weekly_remaining` at or under 0.10, a wake aimed at a Project Head does **not** type into its
Haiku pane. It runs the PH's AGY brain on the PH's unread letters instead, detached.

| Piece | Where |
|---|---|
| `claude_spent(threshold=0.10)`: newest claude row, older than 2 h = not spent, kill switch file `state/claude_out_fallback.off` = never spent, any trouble = not spent | `lib/claude_quota.py` |
| `handle_ph(sid)` — the one helper; `None` = does not apply, wake the pane as before | `tools/mail_wake.py` |
| wake 1: `_wake` for a `project_head-<sid>` box (Console card ends, owner_relay, escalation_watch, portfolio_watch) | `tools/mail_wake.py` |
| wake 2: `_attempt_wake` when the target role is `project_head` (a worker's report; also escalation_watch's re-wake) | `tools/send_to_cto.py` |
| detached runner `python -m tools.mail_wake project_head-<sid> --run-fallback` (setsid, log `state/ph-brain/fallback-<sid>.log`) | `tools/mail_wake.py` |
| tests (106) | `tests/test_claude_out_fallback.py` |

Result for the caller: `{"box", "woke": true, "reason": "claude spent: ran AGY brain"}`. C-level boxes, worker
boxes and every other path are unchanged.

`handle_ph` applies only when all hold: POSIX; sid is 8 hex; Claude spent; host flag `ORG_PH_AGY_BRAIN` on
(without it the PH is a full Claude session and an AGY brain would have none of its context); the PH has a live
record (`state/locks/project_head-<sid>.project` and `.spawned_by` = `cxo:<lane>:<owner sid>`; `cxo-claude.sh`
renames both to `.parked` when the session ends, so a closed PH is not run).

### The runner, per pass (up to 3 passes while letters keep arriving)

1. flock `state/ph-brain/fallback-<sid>.lock`, non-blocking. Held = this runner exits "busy"; the holder's next
   pass takes the new letter (each pass releases the lock before the next, so nothing is stranded).
2. Drain the PH's unread letters no-follow (`mailbox._drain_envelope`). They move to `read/` and stay 7 days.
3. `bash scripts/hub/org-python.sh tools/ph_brain.py turn --ph --project --lane --owner --message=<letters ≤ 4000 chars>`
   — the same wrapper `roles/ph_shell.md` rule 2 uses. `--lane`/`--owner` come from `.spawned_by`
   (`cmo`, `cmo-e785343f`, the form `tools/owner_relay.py` uses).
4. Run the commands in the reply that `roles/ph_shell.md` rule 4 allows, and only those: `ph_brain.py delegate|status`
   and `-m tools.session_charter set`, through `org-python.sh`, with the PH's identity in the env
   (`CXO_ROLE=project_head`, `CXO_SESSION_ID`, no `CTO_SESSION_ID`). `ph_shell.md` has no parser (it is a prompt for a
   Haiku model), so `plan_commands` is new: no shell is ever started; `--ph` must be this PH or is added; the
   `$CXO_SESSION_ID`/`$ORG_PH_PROJECT`/`$ORG_PH_LANE` the shell would have filled in are filled in; an operator
   (`; & | < > ( )`) outside quotes refuses the line; at most 5 commands per turn. Everything else the brain wrote
   is in the log (the whole reply is logged) and is not run.
5. Brain exit ≠ 0: the letters go back into the box as one letter (so the Claude shell still shows them); no retry loop.

## Decisions that differ from the brief, and why

* **Drain happens in the runner under the lock, not in the wake call.** If the wake drained first and the lock was
  held, the letters would be consumed by a run that cannot start. Same observable behaviour, no lost letters.
* **New file refused by the repo guard.** `tools/claude_out_fallback.py` was blocked (task `touches` did not list it),
  so the shared helper lives in `tools/mail_wake.py`, which `send_to_cto` imports lazily. Nothing worked around.
* **No pane scraping.** The brief's item 1 mentions limit strings in the pane ("usage limit", "resets"); the task text
  does not, and it needs a tmux read per wake. Not built.
* `tests/test_mail_wake.py` gets one line in its `inbox` fixture pinning `claude_quota.HISTORY` to a file that does not
  exist. Without it two of its tests (real PH id `b2ff34d1`) would start a **real** detached runner on a live host
  while Claude is spent (shown with a spy plugin: both tests spawn without the pin, none with it).

## Evidence

* `pytest tests/test_claude_out_fallback.py tests/test_mail_wake*.py` — 146 passed.
* Neighbouring suites that reach the wake paths (send_to_cto, mailbox, cxo_crosstalk, escalation_watch ×2,
  mail_envelope_letters, mail_quiet_notice, org_mail_*, org_p2_*, owner_relay, ph_brain, portfolio_watch, w35_wake,
  wake_audit, wake_backoff, wake_screen_gate) — 657 passed, 1 skipped (same as before the change).
* 15 mutants, each breaking one guard (spent gate, flag/record gate, foreign `--ph`, shell operators, flock, requeue,
  command cap, `--message=` glue, multi-pass, both call sites, staleness, kill switch, daily-OR-weekly, provider filter):
  all 15 fail the new tests; the files were restored after each.
* Real subprocess chain once, with a fake `agy` (`AGY_BIN`): `_run_cmd` → `bash org-python.sh` → `ph_brain.py turn` →
  fake agy; the reply's `status` command ran for real (rc 0), a stray `rm -rf` line in the reply did not; the letter
  ended in `read/`. A separate test starts the real detached runner (setsid) and reads its log.
* One test pushes our argv through the real `ph_brain.main` (only `invoke_agy` stubbed): the flags are accepted, the
  letter text reaches the prompt, the brain state gets lane and owner.

## Operating notes

* Kill switch: `touch state/claude_out_fallback.off` (back to waking the pane); `rm` to re-arm.
* Look at `state/ph-brain/fallback-<sid>.log` to see what the brain answered and what it ran or refused.
* The log is append-only and not rotated.

## Not checked / risk

* **Never ran against a live PH with Claude really spent.** No real model, no real Haiku shell, no real tmux were used;
  the smoke test used a fake `agy` and a made-up PH id. First live run is the real test.
* **A question for the CEO from the brain goes nowhere.** `ph_shell.md` rule 5 (`tools/ask_run.py ask`) is not among the
  rule-4 commands the task allowed, so in fallback mode the question stays in the log; nobody is told.
  Suggested follow-up: allow `ask_run.py ask` in `plan_commands`, or raise a `blocker` letter to the owner.
* **The brain's reply is shown to nobody** while Claude is out (log only); the pane stays silent.
* **Not covered:** `send_to_cxo.attempt_wake` called directly (a C-level's own letter to a PH via `send_to_cxo.send`,
  `node_dispatch`). The task named `mail_wake` and `send_to_cto`; `tools/send_to_cxo.py` was not in `touches`. The same
  `handle_ph` call at the top of `send_to_cxo.attempt_wake` would close it.
* **No lock against the Haiku shell's own `ph_brain turn`.** Under 10 % but above 0 Claude may still run the shell, and
  a runner turn could then overlap the shell's on the same AGY conversation. `ph_brain.py` has no turn lock.
* **Reply format is a guess.** The parser takes a command only at the start of a line (after a bullet, `$`, number,
  backtick or fence) in the exact forms `tools/ph_brain.py delegate|status` / `-m tools.session_charter set`, optionally
  behind `bash …org-python.sh` or `python[3]`. `./tools/ph_brain.py`, an absolute path, `cd x && …` or a command inside
  a sentence is logged at most and not run. Check a few real replies in the log and widen if the brains write otherwise.
* winbox PHs (`windows/cxo-claude.ps1`) are POSIX-excluded: `fcntl` is absent there, `handle_ph` returns None and the old
  wake runs. Mac not exercised either (the code is plain POSIX).
* The letters' text is in the runner's argv for the length of a turn (`ps` shows it), as in the existing PH shell path.
* A brain that keeps failing re-queues its letters on every wake; the requeued copy is cut at 4000 chars (the full text
  stays in `read/` for 7 days).
