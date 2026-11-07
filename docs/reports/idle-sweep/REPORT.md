# REPORT task-0d0ccb88

Implemented CEO order O-20261107-2250-c276 in the assigned worktree. No merge,
deployment, live question, save, letter, or disk cleanup was performed.
This report uses the description's explicit `docs/reports/idle-sweep/` location
instead of the generic worker-contract report directory.

## Files changed

- `tools/idle_sweep.py`: zero-model sweep, all-pane readiness, activity signals,
  persisted question/snooze/save state, hourly flock/stamp, off switch, caps,
  caller protection, worker surface teardown, and owner FYI notification.
- `tools/escalation_watch.py`: hourly sweep inside the existing live tick;
  failures do not prevent the existing escalation checks.
- `tools/wake_audit.py`: reviewed gate and embedded-sweep evidence.
- `tests/test_idle_sweep.py`, `tests/test_escalation_watch.py`,
  `tests/test_wake_audit.py`: behavioral, safety and integration coverage.
- `tests/test_escalation_watch_w2.py`: isolate the new live hook in the existing
  watcher tests, preventing test-driven operational side effects.
- `docs/ops/idle-sweep.md`: decisions, state, shutdown controls and limitations.

## Validation

- Final focused tests including existing W2 coverage: **118 passed in 13.59s**.
  Command: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest
  tests/test_idle_sweep.py tests/test_escalation_watch.py tests/test_wake_audit.py
  tests/test_escalation_watch_w2.py`.
- `git diff --check`: passed.
- The three explicitly requested files also passed on their own: **90 passed
  in 6.27s**, before adding the final notification-retry regression test.
- Full suite launched in the background with output to
  `/tmp/idle-sweep-full-suite-final.log`, using `TMPDIR=/tmp/idle-sweep-tests`
  and the shared virtualenv on PATH. **Incomplete / blocked**: interrupted
  (exit 130) at 15% after approximately five minutes without progress.
  Its progress stream recorded 2,142 pass markers, 18 skips, 79 failures and
  87 errors. These are partial progress counts, not a completed pytest summary.
  The interrupted process emitted no final traceback summary. A separate
  first-failure run captured the socket traceback in
  `/tmp/idle-sweep-first-failure.log` (1 failed, 141 passed, 1 skipped).
  Full-suite acceptance is **not met**; do not infer a green suite from the
  focused test result. The final notification-retry change was verified by
  the focused run, after this background run had started.
- Initial runs were interrupted to fix test scratch-directory selection:
  the inherited TMPDIR and `/tmp` both cause the existing database guard to
  detect a `.git` ancestor. A dedicated `/tmp/idle-sweep-tests` resolved this;
  `scripts/test_dev_tab_color.py` then passed all 13 tests.

## Host dry-run

Command: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/idle_sweep.py --dry-run`

```text
idle sweep skipped: RuntimeError: tmux failed: error connecting to /tmp/tmux-0/default (Operation not permitted)
```

Exit 1. The sandbox denies the host's tmux socket, so no inventory or operational
actions were possible. The dry-run did not update state or the hourly stamp.

## Not checked / risk

- Live tmux inventory, card delivery/cancellation, actual parking, and owner
  letter delivery were not exercised; subprocess/API behavior is mocked in tests.
- The mandatory `pane_screen.prompt_ready` classifier currently recognizes
  Claude-style prompts. Unknown Codex/AGY/shell screens are conservatively
  skipped; adding UI recognition is outside this change.
- The hub automatically expires cards at seven days. Already-expired cards
  cannot be cancelled again; pending cards are cancelled before force-save.
- Remote card creation and local persistence are not one transaction. A crash
  between them can orphan a card. Letter delivery likewise has a narrow
  retry/duplicate window. Preserve the state file across deployments.
- The existing session-kill path preserves UUIDs but treats status-recording
  and memory-sync failures as best-effort. Its existing transient lock cleanup
  remains; worktrees, Work directories and transcripts are retained.
- The existing watcher unit has a 120-second timeout. Slow hub or save calls
  can interrupt a sweep; the hourly stamp limits retries until the next hour.

## Blockers

- Sandbox socket restrictions block the real host dry-run and existing tests
  that bind sockets. The first confirmed unrelated failure is
  `scripts/test_drive_photo_broker.py::test_peer_uid_not_in_allowlist_is_refused_over_a_real_socket`,
  at `server_sock.bind`: `PermissionError: [Errno 1] Operation not permitted`.
  `git diff main -- scripts/test_drive_photo_broker.py lib/db.py` is empty
  (worktree HEAD `341d0dd4`, local main `34d25105`); neither baseline file changed.
  Thus the requested full-suite failure set restricted to `{osv-scanner}`
  cannot currently be claimed in this environment. No approval bypass was attempted.

## Skill learning

- (none)
