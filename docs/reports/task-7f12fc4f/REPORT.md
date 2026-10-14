# REPORT task-7f12fc4f

Runner: codex
Exit code: 0

Reviewed `fda6f141`. Findings:

- **BLOCKING — `tools/escalation_watch.py:340`**: The guarded wake calls the legacy transport, which sends Enter, waits 0.3 seconds, then sends another unconditional Enter (`tools/agent_transport.py:190–198`). A permission prompt appearing after submission can receive that second Enter. Capture and sending also resolve the active pane separately. **Fix:** pin the captured pane ID, revalidate before submission, and remove unconditional rescue Enter.

- **MAJOR — `tools/escalation_watch.py:296`**: A group member can pre-create `state/escalation_watch.json` as a directory. Reading rejects it, but replacing it with a regular file fails; `save_state()` silently swallows that failure. Every invocation consequently sends initial notifications again, defeating both caps. Sticky permissions do not prevent creating this entry. **Fix:** provision state in a root-owned, non-group-writable directory and fail visibly before sending when persistence is unavailable.

- **MAJOR — `tools/escalation_watch.py:410`**: An empty scan never calls `nudge()`, so completed episodes remain persisted and pending digests never flush. If a waiting prompt disappears and later returns with the same subject, an exhausted episode suppresses the new alert. **Fix:** call `nudge()` on every enabled scan, including empty findings; test through `main()`.

- **MAJOR — `tools/escalation_watch.py:281`**: Dropping future timestamps resets legitimate rate-limit state after a backward clock adjustment. An in-memory probe produced two digest letters after a one-second rollback; episode counters reset similarly. **Fix:** retain counters and conservatively normalize timestamps, or use boot-aware monotonic elapsed time.

- **MINOR — `tools/escalation_watch.py:275`**: State writes are unbounded, but reads retain only the final 1 MiB. Oversized JSON becomes invalid and silently resets all notification history. A synthetic 16,000-host probe saved 1,156,967 bytes and subsequently loaded zero episodes. **Fix:** bound stored state and handle oversized snapshots explicitly rather than parsing their tail.

The direct waiting-finding route excludes its subject, and failed/non-ready captures suppress the immediate wake call. However, a waiting session can still receive letters as another finding’s owner, COO, blocker holder, or digest recipient; exclusion is not global.

The text fix rejects malformed box IDs and host names and omits display names. Validated identifiers still appear in letters. State reads check ownership, permissions and link count; temporary-file replacement avoids writing through a destination symlink.

No obvious unit restriction blocks the named dependencies: there is no `PrivateTmp`, Unix/network address families remain allowed, and Infisical’s run path reads credentials and executes the command. Runtime hardening remains unverified.

Validation: the required pytest command failed because `.venv/bin/python` is absent. The assigned worktree is at `67911929`; review used Git objects at `fda6f141`. The PR body was unavailable. No repository files were changed or report file written, honoring the explicit read-only instruction.

VERDICT: fix first