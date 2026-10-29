# task-aacebd72: CEO question cards enforced, and the requester woken when a card ends

## Summary
Part A: `scripts/hook-phone-only-commands.py` gets a second Stop-hook check, `question_offenders()`, that blocks a
C-level or PH reply which asks the CEO something in chat with no card in the turn. Part B: a new
`python -m tools.mail_wake <box>` wakes the session that waits on an unread mailbox letter, and
`ask_run.py wait` accepts `--timeout` as an alias of `--max-wait`.

## Files Changed
- scripts/hook-phone-only-commands.py: `turn()` returns the turn's text and tool_use blocks (`turn_text()` keeps
  its signature and delegates); new `question_offenders()` / `_raises_card()`; `decide()` returns one block that
  carries both reasons when both checks hit. The `!` check is untouched.
- tests/test_hook_phone_only_commands.py: +64 cases (every MUST block and MUST pass from the brief, plus the
  exemption shapes, a roster-drift test against `c_level_roles()`, and the verbatim reason).
- tools/mail_wake.py: new CLI (see Notes).
- tests/test_mail_wake.py: new, 40 cases.
- tools/ask_run.py: `wait --max-wait` also answers to `--timeout` (same dest).
- tests/test_ask_run.py: `test_wait_timeout_is_an_alias_of_max_wait`.
- tests/test_c_level_roles.py: one `_ALLOWED_SUBSETS` row for the hook's role set. Not in the brief; see Notes.
- docs/reports/task-aacebd72/REPORT.md: this file.

## Commits
- 9b74453c: hook-phone-only-commands: block a C-level or PH that asks the CEO in chat with no question card
- 98499d8c: ask_run wait: accept --timeout as an alias of --max-wait
- be19b407: mail_wake: wake the session that waits on an unread mailbox letter (tools/mail_wake.py, its tests, the `_ALLOWED_SUBSETS` row, this report)

## Tests
- ran: `.venv/bin/python -m pytest tests/test_hook_phone_only_commands.py tests/test_mail_wake.py tests/test_ask_run.py`
- passed: 233 (73 hook + 40 mail_wake + 120 ask_run)
- failed: 0
- skipped: 0
- also ran, because the change reaches them: `tests/test_c_level_roles.py` (26 passed, 2 skipped, after the row below;
  it failed without it), `tests/test_ask_run_questions.py`, `tests/test_wake_audit.py`,
  `tests/test_mail_envelope_letters.py` (all pass; 562 passed together with test_c_level_roles before the fix).
- fails-without-the-change, checked by mutation, not assumed: with `question_offenders` neutered 28 hook tests fail;
  with the exemptions removed 17 fail; with the fence / `>` / quote skips removed 4 fail. With `mail_wake` reading
  letters through a plain glob and no symlink guard, the symlinked-box, symlinked-letter and read-letter tests fail;
  with the unread check removed 7 fail. The `--timeout` test fails on the old `ask_run.py` with
  `unrecognized arguments: --timeout 7`.

## Issues / Blockers
- none.

## Notes for Reviewer
**What the change reaches (listed before the first edit).**
- `scripts/hook-phone-only-commands.py`: registered at `.claude/settings.json:171` as a Stop hook run with `python3`
  (stdlib only, checked under 3.12). Only its own test imports it. `turn_text()` has no other caller.
- `tools/ask_run.py` `wait` parser: callers of the flag are `cmd_wait` (reads `args.max_wait`, unchanged) and the
  existing `--max-wait` tests. `create` has its own, unrelated `--timeout`; the two sub-parsers do not share it.
- `tools/mail_wake.py` is new and has no caller yet. The Console must call it.

**Part A decisions.**
- `PHONE_ONLY_GUARD=off` stays the switch for the whole hook, as it is today, so it also turns the question check
  off. `CARD_GUARD=off` turns off only the question check. Your brief said "the `!` check exactly as it is"; I read
  that as not changing the early return.
- A failure inside `question_offenders` is caught and logged to stderr, so a bug there cannot take the `!` check
  down with it.
- `CXO_ROLE` is compared lower-cased and stripped.
- Quotes are stripped per line. A quote that spans lines is not recognised; I chose that over letting one stray `"`
  hide the rest of a reply.
- `tests/test_c_level_roles.py::test_no_partial_roster_literal_in_runtime_code` failed on the hook's five-role set
  (a literal of 3+ roles that misses `coo`). That test names deliberate subsets in `_ALLOWED_SUBSETS`; I added the
  hook there with the reason. CI runs the full suite, so the PR would have been red without it.
- Known false-positive shapes, each costs one extra turn at most (`stop_hook_active` stops the second block): a line
  ending in `?` that contains `คุณ` as part of คุณภาพ, คุณธรรม or คุณสมบัติ, or the word "you" ending a question that
  is not to the CEO. The brief's rule says "contains คุณ", so I did not carve out exceptions.

**Part B: `tools/mail_wake.py`.**
- Box name must fullmatch `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. A symlinked box is refused (reason `box is a symlink,
  refused`, nothing read). Unread letters are read through `lib.mailbox._BoxView`, which opens the box and each
  letter no-follow, so a symlinked or FIFO letter does not count.
- C-level or PH box (`<role>-<sid>`, role in `c_level_roles()` or `project_head`): `send_to_cxo.attempt_wake(role,
  sid, label)` straight away. No `wake_due`/debounce and no `note_wake`. That includes `coo`; its tmux name is
  `sompong` via `session_name.tmux_name`.
- Worker box (`<role>-task-<8 hex>`): `agent_transport.attempt_wake("wd-<8 hex>", label, "mail_wake")`. That is the
  call `send_to_worker._attempt_wake` makes; I did not call `send_to_worker._attempt_wake` itself because it
  discards the bool, and I wanted `woke` to be true only when the nudge reached a live pane. The session name is
  derived from the box name with `tmux_session.session_name_for`, the one function `delegate.py` uses to set
  `task["tmux_session"]`, so **no hub lookup is needed**. A task on a non-tmux backend has no `wd-` session and
  comes back `woke: false`.
- Anything else: `woke: false, reason: "not a session box"`.
- Output is one JSON line `{"box","woke","reason"}`. Exit 0 whenever it ran, 2 for an invalid box name or a missing
  argument, and `wake()` catches everything else (`reason: "error: <ExceptionType>"`).
- Runs without `ORG_DB_URL` for C-level, PH and worker boxes: tested in-process with the ledger functions made to
  raise, and as a subprocess with `ORG_DB_URL` removed. It does need PyYAML (`lib.config` imports it), so the Console
  must call it with the venv python. Under a bare `python3` without PyYAML a C-level wake returns `woke: false,
  reason: "error: ModuleNotFoundError"` and exit 0.

## Not checked / risk
- Nothing calls `tools.mail_wake` yet: the Console change (a separate project) is not part of this branch, so the
  idle-PH problem is not fixed until it calls the CLI once per ended card.
- The real tmux nudge was never sent. Every wake in the tests is a recorder, and the one real `attempt_wake` run
  has `tmux_session.has_session` stubbed to false. Whether the Console's process user shares root's tmux server
  (`/tmp/tmux-0/default`) is unchecked; run as another user it reaches no session and reports `woke: false`.
- IRON §64 says one event wakes once, and the brief asks for no debounce. A second `mail_wake` call for the same box
  while the letter is still unread nudges again. `attempt_wake`'s own pane checks limit the harm; the Console should
  call it once per ended card.
- The hook was tested on fixtures only (the brief forbids reading real transcripts). Its false-positive rate on live
  C-level prose is unmeasured; the first live day will show it. `PHONE_ONLY_GUARD=off` or `CARD_GUARD=off` in a
  session's env is the escape hatch.
- I did not run the full suite; CI does.

## Skill learning
- MISSING [ALL_Protocol_RunInbox §Question cards] : the skill says to `ask_run_wait` a card but not that the hub's result letter wakes nobody (IRON §64.5 says it in one clause); it should name `tools/mail_wake.py` once the Console calls it, and give `wait`'s flag as `--max-wait` (`--timeout` now works too) · evidence: task-aacebd72
- COSTLY [no owner] : `tests/test_c_level_roles.py` fails any new literal of 3+ C-level roles that misses `coo`, and nothing in the brief or the CLAUDE.md said to look there; I found it by running related tests. A brief that adds a role set should name it · prevented by: running `tests/test_c_level_roles.py` whenever a role tuple is written
