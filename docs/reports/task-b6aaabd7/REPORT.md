# REPORT task-b6aaabd7

## Files changed
- tools/pane_dialog_watch.py: Added one-pass read-only tmux watchdog, shared C-level roster filtering, singleton `sompong` COO support, centralized dialog markers, persistent first-seen/delivery state, locking, atomic state replacement, and retry on capture/delivery failure.
- scripts/install-pane-dialog-watch.sh: Added install/uninstall/status for a systemd oneshot service and 60-second timer using the repository .venv Python; follows install-drive-broker.sh conventions.
- tests/test_pane_dialog_watch.py: Added fake tmux/notifier coverage for timing, deduplication, clearing, role filtering, markers, text limits, failure recovery, disappearing panes, independent panes, and environment overrides.
- docs/reports/task-b6aaabd7/REPORT.md: Recorded implementation, validation, and rollout limitations.

Notification helper: `lib.telegram_out.send_to_ceo` delivers directly to the CEO's Telegram chat with explicit delivery success/failure. This suits an unattended session needing his hands; `lib.notify` only logs or provides optional Mac desktop banners, and tools/email_ceo.py is absent. Only the first matching dialog line is included, capped at 200 characters; surrounding pane content is not sent or persisted.

Session naming was read from scripts/cto-claude.sh and scripts/cxo-claude.sh: `<role>-<id>` plus singleton COO `sompong`. The role roster comes from lib.roles.c_level_roles().

Runtime overrides: `PANE_DIALOG_WATCH_STATE` (default state/pane-dialog-watch.json), `PANE_DIALOG_WATCH_SECONDS` (default 300). Run from the repository with `.venv/bin/python -m tools.pane_dialog_watch`.

Installer setup: CTO supplies `PANE_DIALOG_WATCH_ENV` pointing to an existing absolute systemd environment file with TELEGRAM_BOT_TOKEN and TELEGRAM_CEO_CHAT_ID, and optionally `PANE_DIALOG_WATCH_USER` (default root). Use the account owning the C-level tmux server, with repository state write access. The installer does not copy credentials. PrivateTmp is deliberately omitted so the normal tmux socket remains visible.

## Tests
Command:
`HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_pane_dialog_watch.py -o addopts="" -p no:warnings`

Pytest result: `18 passed in 0.80s` (18 collected, 0 failed).

Command: `bash -n scripts/install-pane-dialog-watch.sh`

Result: passed, exit 0.

## Not verified
- No installer execution, service operations, live tmux scan, or real notifications were performed.
- CTO must verify the service account sees the intended Contabo tmux server, credentials reach the CEO, state is writable, and the timer runs after installation. A separate user's tmux server is not included in `list-panes -a`.
- Detection uses marker text on the visible pane, not Claude internals. Quoted marker text can resemble a dialog; dialogs cleared and replaced entirely between scans cannot be distinguished. No scrollback is scanned.
- A process crash after delivery but before saving its delivery flag can cause a repeated notification; state is saved after each notice to minimize that window.
- Mac/winbox deployment is outside this Contabo systemd task.

## Blockers
- None. Installation and live verification belong to the CTO after review.

## Skill learning
- (none)
