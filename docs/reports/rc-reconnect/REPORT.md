# Remote Control reconnect

Implementation and validation: [task report](../task-60bc74d6/REPORT.md).

The watcher now scans local tmux panes each tick. Only the latest disconnected RC status plus an empty idle prompt permits a reconnect. Worker panes are excluded; sompong without RC naturally has no matching status. Attempts are limited to one per pane per 30 minutes, with three unresolved attempts producing one owner FYI and stopping retries. Login loss produces one quiet cto-fresh blocker and no typing.

Use `python tools/rc_reconnect.py --dry-run` for read-only inspection. Create `state/rc_reconnect.off` to disable it. State is in `state/rc_reconnect.json`, under ORG_ROOT when configured. A later connected/active observation clears the failure streak; operators can also reset a stopped pane's state after investigation.

Validation: required pytest command passed 73 tests. Claude version is 2.1.319; help confirms the Remote Control launch flag. No live keys or letters were sent.

## Not checked / risk
- Host tmux access was denied by the worker sandbox (Operation not permitted). Dry-run failed closed; the three reported panes could not be listed or inspected.
- The installed version's interactive footer hint and successful app reattachment remain unverified. Runtime prefers /rc or /remote-control shown in the capture, falling back to /remote-control.
- Automatic recovery is implemented but not deployed from this worktree. Failure assessment occurs on subsequent ticks, not by assuming Enter means RC connected.
- Auth status uses the watcher's account. Capture/send races remain possible; the shared transport guards drafts and dialogs before each key stage.
