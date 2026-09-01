---
name: session-restart
owner: CTO
origin: mooniex-org
scope: >-
  LAST RESORT — tears down and rebuilds the whole tmux+claude stack
  (session-kill.sh --status saved, then spawn-cto.sh/spawn-cxo.sh --resume)
  with the SAME session id and the SAME resume UUID, for when tmux itself is
  wedged, wrongly named, or gone while the process lingers — i.e. when
  terminal-restart's `respawn-pane` cannot even be delivered. Never use this
  when the pane's claude is merely stuck/stale/confused and tmux is fine —
  see terminal-restart, which is far cheaper and never closes the tab.
description: Rebuild a C-level session whose tmux itself is broken — wedged, wrongly named, or gone while the process lingers. Trigger on /session-restart and when the CEO or CTO says "tmux ค้าง", "session หาย", "tmux session ผิดชื่อ", "attach ไม่ได้", "tmux server พัง", or terminal-restart itself reports it cannot deliver respawn-pane. Not for a claude process that is merely stuck/confused with tmux otherwise healthy — see terminal-restart.
created_by: human
audience: [cxo]
---

# Session Restart — last resort: rebuild the whole stack

**Repair the innermost layer that is actually broken. Never tear down a layer
that still works.** (task-b0b3f602)

```
iTerm tab  →  tmux session <role>-<id>  →  pane  →  claude
```

| symptom | broken layer | tool |
|---|---|---|
| claude runs stale code / is stuck / is confused | claude | [[terminal-restart]] |
| tmux session wedged, wrong name, or gone while the process lingers | **tmux + locks** | **this skill** |
| tab closed but tmux fine | tab | `/terminal-open` |

Try [[terminal-restart]] first, always — it is the cheap, non-destructive
repair (tmux session and iTerm tab both survive). Reach for this skill only
when tmux itself is the thing that's broken, so `respawn-pane` cannot even
be delivered to it.

## What this actually does

Unlike terminal-restart, this **does** tear the stack down — a new tmux
session and a new iTerm window get built, not the same ones. What survives
is the *identity*: the same short session id, and the same resume UUID, so
DEV reports and CEO history keep routing to it.

1. **Capture id + UUID first**, to a temp file OUTSIDE `state/locks/` —
   `session-kill.sh`'s `reap_locks` deletes the `.lock`/`.run`/`.tty`/
   `.winid`/`.watcher-pid`/`.topic` family (it deliberately preserves
   `.uuid` — `tools.session_name.KEEP_SUFFIXES` — but this capture survives
   even if `.uuid` is later hand-deleted too).
2. `session-kill.sh --status saved <name>` — **saved**, not `closed`: the
   work is not finished, only parked.
3. Rebuild via `spawn-cto.sh --id <id> --resume <id>` (cto) or
   `spawn-cxo.sh --role <role> --id <id> --resume <id>` (cmo/cgo/cfo) — both
   flags already exist on those launchers; this does not invent a new
   invocation. `--resume <id>` resolves the short id back to the full UUID
   via the very `.uuid` file `reap_locks` preserved.
4. Same verify-or-shout-loudly step as terminal-restart.

## Before acting — say both of these out loud

- **Resume is not free.** The rebuild re-reads the whole prior transcript
  back in — the script prints a rough size proxy (the per-session log file
  size); state it and let the operator decide.
- **The in-flight turn is lost.** Whatever the pane was doing at the moment
  of the kill does not come back. Files on disk and worktrees are untouched
  — only the tmux+claude stack is torn down and rebuilt.

## Hard gate — refuse a session that owns live work

Same gate as terminal-restart, and for the same reason: **refuse to rebuild
a session that owns any task in `pending`, `in_progress`, `rate_limited`, or
`blocked_human`** — tearing it down orphans the DEV(s) it supervises.
`--force` overrides it and names, out loud, exactly which tasks it
overrode. A session with no `.uuid` is refused unconditionally — without the
resume key there is nothing to rebuild *into*, only a fresh, memoryless
session.

## Running it

```bash
bash scripts/session-restart.sh                # this session (reads env)
bash scripts/session-restart.sh cfo-a1b2c3d4    # a different session, by name
bash scripts/session-restart.sh --force cfo-a1b2c3d4
```

Rebuilding **this** session: the whole sequence (kill, respawn, verify) is
deferred via a nohup'd, SIGHUP-proof background block — same reasoning as
terminal-restart, one level up: the command tearing the pane down is itself
running inside it. Any verify failure is written, loudly, with the resume
UUID, to the session's own log file.

Rebuilding a **different** session: no self-kill risk, runs synchronously,
reports the verified result directly.

## Report

State: whether the check passed or was `--force`d (and over what), the
resume-cost + in-flight-loss warnings given, where the identity was
captured, and the verify result (pid found in the new stack, or the loud
failure + UUID for a manual resume).
