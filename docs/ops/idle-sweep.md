# Idle session sweep

CEO order O-20261107-2250-c276. `tools/idle_sweep.py` is deterministic Python:
no model calls, polling prompts, wakes, new service, or new timer (IRON §53/§64).
The existing `escalation_watch.py --nudge` tick calls it. An exclusive flock on
`state/idle_sweep.stamp` serializes runs; the timestamp reserves at most one run
per hour, including failed runs. A manual live invocation uses the same gate.

Every local tmux session is inspected, across all windows and panes. `sompong`,
`runwatch-*`, the invoking tmux session, and sessions whose lock PID is the
sweep or its parent are protected. Every pane must pass
`lib.pane_screen.prompt_ready`, both on inspection and immediately before saving.
Unrecognized prompts fail closed, including worker UIs the classifier cannot recognize.

C-level activity comes from `state/locks/<name>.uuid` and the matching
`~/.claude/projects/*/<uuid>.jsonl` mtime. Worker sessions named
`mooniex-task-*` or `wd-task-*` use the newest launcher/pane log, worktree
directory mtime, or hub task `updated_at`. Hub failure skips the worker rather
than using a stale database fallback. Worktree directory mtime is not a recursive
file scan; launcher HEARTBEAT is deliberately not activity. Missing signals are
logged and skipped. Project labels come from the task row or pane directory.

At three idle days, one CTO question offers `ปิด (save ถาวร)` and `ทำต่อ 3 วัน`.
`state/idle_sweep.json` records the card ID, raised timestamp and snooze deadline.
Continue snoozes for three days from observation; close parks the session with
`session-kill.sh --status saved`. Answers must pass ask_run's passkey provenance
validation. After seven unanswered days a pending card is cancelled before
`--status force_saved`. Cards already expired by the hub's seven-day maximum
are terminal and cannot be cancelled again; they also qualify for force-save.
Unknown answers/statuses and hub errors cause no save.

Workers use the launcher's tmux session teardown, without changing their task
row. C-level resume UUIDs are retained by session-kill. No worktree, Work directory
or transcript is deleted. Existing session-kill transient lock cleanup still
applies. A `fyi` letter, with no wake, goes to the `cxo:role:id` in `.spawned_by`,
otherwise CTO Main (`cto-active`, fallback `fresh`). Pending notifications are
persisted and retried, including after a session disappears. Each run is capped
at five new cards and three saves.

## Controls

Create `state/idle_sweep.off` to disable the sweep; remove it to enable it again.
Run `python3 tools/idle_sweep.py --dry-run` for read-only inspection: no cards,
cancellations, saves, letters, state changes or hourly stamp updates. Read-only
tmux commands and reads of existing cards still occur. Run from the deployed
checkout to use its locks and state; a development worktree has separate state.
Missing tmux access prints a failure and returns nonzero, taking no action.

State corruption fails closed. Preserve the state file when deploying: deleting
it can orphan an open card. There is a narrow crash window between successful
remote card creation and local state persistence, and between letter delivery
and its local acknowledgement; these APIs have no shared transaction.
