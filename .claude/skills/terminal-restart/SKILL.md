---
name: terminal-restart
owner: CTO
origin: mooniex-org
scope: >-
  Replaces a stuck/stale/confused claude process IN PLACE via `tmux respawn-pane
  -k` — same pane, same window, same tmux session. The common-case repair.
  Refuses (or shouts loudly) if the session owns live work or has no resume
  UUID. Does NOT touch tmux itself — if tmux is the broken layer (wedged,
  wrongly named, or gone while the process lingers), this is the wrong tool;
  see session-restart.
description: Restart a stuck/stale/confused claude process without losing the tmux session or the iTerm tab. Trigger on /terminal-restart and when the CEO or CTO says "claude ค้าง", "claude งง", "restart claude", "รันโค้ดเก่า", "session นี้ทำงานแปลกๆ", "claude stuck", "reload claude", or a running session is clearly executing stale/pre-merge code. Not for a wedged tmux session or a gone tab — see session-restart / terminal-open.
created_by: human
audience: [cxo]
---

# Terminal Restart — replace claude in place, leave tmux alone

**Repair the innermost layer that is actually broken. Never tear down a layer
that still works.** (task-b0b3f602)

```
iTerm tab  →  tmux session <role>-<id>  →  pane  →  claude
```

| symptom | broken layer | tool |
|---|---|---|
| claude runs stale code / is stuck / is confused | **claude** | **this skill** |
| tmux session wedged, wrong name, or gone while the process lingers | tmux + locks | [[session-restart]] |
| tab closed but tmux fine | tab | `/terminal-open` |

If the symptom is tmux itself — not claude — stop and use `session-restart`
instead. Running this skill against a wedged tmux will fail to even deliver
`respawn-pane`; that failure IS the signal to switch tools, not to retry.

## What this actually does

`tmux respawn-pane -k -t "<session>" "bash <run-file>"` — `-k` kills the
pane's current process and runs the new command in the **same pane, window
and session**. The iTerm tab never closes, the tmux session never dies, and
`state/locks/<name>.winid` stays correct because the window never changed.
If the relaunch itself fails, tmux is still there and the session is
recoverable — that is the entire reason this is preferred over a rebuild.

The run-file re-exports the exact same env the original launch used and
execs the same launcher (`cto-claude.sh` / `cxo-claude.sh`) with `-r <uuid>`
appended — the launcher's own logic already turns that into
`--fork-session` (it does this for every `-r`/`-c` invocation already; see
`FORK_ARGS` in both scripts). This does not hand-construct a new `claude`
invocation — reusing the launcher is what keeps MCP config, tool whitelist,
and tab-title machinery from drifting out of sync with a second copy.

## Before acting — say both of these out loud

- **Resume is not free.** `-r <uuid>` re-reads the whole prior transcript
  back in — a long session costs real tokens to restart. The script prints a
  rough size proxy (the per-session log file size); state it and let the
  operator decide, especially on a long-running session.
- **The in-flight turn is lost.** Whatever tool call was running in the pane
  at the moment of the kill does not come back — there is no partial-resume.
  Files already written to disk and worktrees are untouched; only the
  in-memory turn is gone.

## Hard gate — refuse a session that owns live work

**Refuse to restart a session that owns any task in `pending`, `in_progress`,
`rate_limited`, or `blocked_human`.** Killing its claude orphans the DEV(s)
it is supervising — their reports would land with nobody reading them. The
script queries `tasks` by `owner_cto = <session id>` and names exactly which
tasks are blocking it.

`--force` overrides this one gate (never the missing-UUID refusal below) —
and the script names what it overrode, out loud, so an operator who forces
past it cannot later claim they didn't know.

A session with **no `.uuid` file** is refused unconditionally, `--force` or
not: without the resume key, "restart" would actually be an amnesia event —
a fresh session with no memory of what it was doing, not a restart of it.

## Running it

```bash
bash scripts/terminal-restart.sh                 # this session (reads env)
bash scripts/terminal-restart.sh cto-a1b2c3d4     # a different session, by name
bash scripts/terminal-restart.sh --force cto-a1b2c3d4
```

Restarting **this** session (the common `/terminal-restart` case): the
script defers the actual `respawn-pane` a few seconds (nohup'd, SIGHUP-proof
— same shape as `session-kill.sh`) so its own message flushes before the
pane dies, then verifies in the background and writes any failure — loudly,
with the resume UUID — to the session's own log file, since there is no
terminal left to print to by then.

Restarting a **different** session: no self-kill risk, so it runs
synchronously and reports the verified result directly.

## Verify it actually came back

~25s after the respawn, confirm a live `claude` process exists in the pane
(walking process descendants, not `tmux`'s own idea of the foreground
command — that was observed reporting a perfectly healthy session as "bash",
not "claude", because the launcher runs claude as a plain child, not an
exec'd replacement). On failure: error loudly and print the resume UUID so a
human can `bash scripts/spawn-cto.sh --resume <id>` by hand.

## Report

State: whether the check passed or was `--force`d (and over what), the
resume-cost + in-flight-loss warnings given, and the verify result (pid
found, or the loud failure + UUID).
