---
name: terminal-open
owner: CTO
origin: mooniex-org
scope: >-
  Reattaches an iTerm2 window on the Mac to a C-level chat that is ALREADY running
  in tmux — the closed-tab recovery. Never spawns a new chat, never resumes a
  transcript, never kills anything. Works when typed from the phone: the agent runs
  on the Mac, so the Mac window reappears.
description: Bring back the Mac iTerm window for a C-level chat whose tab was closed — same session, same scrollback. Trigger on /terminal-open and when the CEO says "เปิด terminal กลับมา", "ปิด tab ไปแล้วเอากลับ", "เอา terminal คืนมา", "show the terminal", "reattach", "กลับเข้า session เดิม", "open iTerm back".
---

# Show Terminal — put the closed iTerm tab back

Closing a C-level iTerm tab does **not** end the chat. The chat runs inside a
tmux session named `<role>-<id>`; the iTerm tab is only one of its clients, and
the phone Console (`mooniex-console` `src/tmux/bridge.js`) is another. Closing
the tab detaches one client. This skill attaches a new one.

Contrast — do not confuse these:

| want | use |
|---|---|
| the **same** chat back on screen | **this skill** — `tmux attach`, live process |
| a **new** chat | `spawn-cto.sh` / `spawn-cxo.sh` |
| a new chat that **replays an old transcript** | `spawn-cto.sh --last` / `--resume <id>` |
| just *see* which sessions exist | [[session-list]] |

`--last` / `--resume` are **not** this. They start a fresh tmux session and
feed Claude an old transcript — a copy, not the running thing. Only `tmux
attach` gives the CEO the process that is still executing.

## Run it

```bash
bash /Users/gob/Projects/Agents/scripts/terminal-open.sh            # THIS session
bash /Users/gob/Projects/Agents/scripts/terminal-open.sh --orphan   # newest one with no client
bash /Users/gob/Projects/Agents/scripts/terminal-open.sh --list     # inventory
bash /Users/gob/Projects/Agents/scripts/terminal-open.sh 8172e36d   # a specific id
```

Bare `/terminal-open` → **no flag**. That attaches the session the command was
typed in, which is the whole point when the CEO is on the phone: they are
looking at the chat and want the Mac window back on *that* one.

`--mac` is accepted and ignored — the Mac is the only place iTerm exists. Say
so once rather than erroring.

## Picking the target

- **CEO is chatting in the session they want** → no flag.
- **CEO closed a tab earlier and is now somewhere else** → `--orphan`. It picks
  the most recently active session with `attached=0`, which is exactly what a
  closed tab leaves behind (the phone attached would make it `1`).
- **Several candidates, or CEO names one** → run `--list`, relay the table, let
  the CEO pick. Do not guess between two detached sessions.

## After it runs

Report the session name it attached (`iTerm window attached -> cto-8172e36d`).
Running it twice is harmless — tmux takes any number of clients — but a second
window on a session that already has one is usually a mistake; check `--list`
first if unsure.

If it prints `not inside a C-level tmux session`, the caller is a plain shell
(a DEV tab, or a chat started before the 2026-08-07 tmux rollout). Sessions
started before that rollout were never wrapped in tmux and **cannot** be
reattached — a running process cannot be moved into tmux. Say that plainly
instead of retrying.

## Why DEV tabs are not covered

DEV tabs spawn with `backend = "iterm"` by default (`tools/delegate.py:571`,
CEO preference recorded in `config/projects.yaml:54`) — a plain pty, no tmux.
Closing a DEV tab really does kill it. Recovery there is `tools/resume_dev.py`,
not this.
