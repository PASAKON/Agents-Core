# Waking a Windows Terminal tab (W3.5)

Status: **measured and working in the desktop session; not yet live.** Two things stand
between this and `woke: true`: the CEO runs `windows\register-org-tasks.ps1` once, and
`tools/node_dispatch.py` calls `agent_transport.wake_windows_tab` (see "Wiring").
Numbers and method: `docs/reports/task-109734f6/REPORT.md`.

## What it does

A letter for a C-level session on winbox is already written to its mailbox by
`node_dispatch`. This adds the nudge the tmux path gives a Mac/Linux session: it types
`[New message from <LABEL>]` + Enter into that session's Windows Terminal tab, so the
session reads its mailbox.

```
sender (ssh, session 0)                     console session (the desktop)
--------------------------                  --------------------------------------------
write state\wake\requests\<id>.json   --->  MooniexOrgWake (registered once by the CEO)
schtasks /run /tn MooniexOrgWake            windows\wake-request.ps1   validates the request
poll state\wake\results\<id>.json   <---    windows\wake.ps1           finds the tab, checks, types
```

Python entry point: `tools.agent_transport.wake_windows_tab("<role>-<sid>", "<LABEL>")`
returns `{"woke": bool, "why": str}`. `woke` is true only when `wake.ps1` exited 0, which
means the keys went to a tab that was verified in front with keyboard focus in it.
`attempt_wake` calls it on win32; on POSIX it is byte-for-byte what it was
(`tests/test_w35_wake.py` pins that).

## The one-time step (CEO, at the winbox desktop)

```
powershell -NoProfile -ExecutionPolicy Bypass -File windows\register-org-tasks.ps1
```

Run it from the checkout that runs `node_agent` (the task is bound to that checkout's
`windows\` and `state\`). It registers `MooniexOrgWake`: Interactive logon, no
elevation, **no trigger** (runs only when something runs it), 2-minute limit. Undo:
`... register-org-tasks.ps1 -Remove`.

Why a person and not the agent: registering a task from an ssh command was refused by the
auto-mode classifier as "Unauthorized Persistence" (2026-09-30). That is the right call for
a persistent task, so nothing in this repo registers it. Until it exists,
`wake_windows_tab` returns `woke: False` and says so.

## How `wake.ps1` decides it may type

It sends a key only when all of this is true, checked immediately before the text and again
before Enter:

1. exactly **one** Windows Terminal tab matches the title (counted through UI Automation
   across all WT windows; a window's own title shows only its selected tab, so counting
   windows cannot see a second match);
2. that tab's window is the **foreground** window, class `CASCADIA_HOSTING_WINDOW_CLASS`;
3. the foreground title matches (exact, or contains the token with `-Contains`);
4. **keyboard focus is in a `TermControl`** of that process. This one is here because of a
   measured failure: checks 1-3 passed while the tab strip held focus and every key was
   swallowed (exit 0, 0 of 5 delivered).

Otherwise it exits 3 and sends nothing (2 = no/ambiguous match, 4 = no desktop, 64 = bad
arguments). It raises the window with `AppActivate`, then `SetForegroundWindow` +
`AttachThreadInput`, then `SwitchToThisWindow`, re-checking after each. It never sends a
synthetic ALT to win the foreground: that is itself a key into whatever is in front.

Methods (`-Method auto` tries them in order): `appactivate` reaches a tab that is already
selected; `uia` selects a background tab with `SelectionItemPattern` and puts focus in its
terminal with `SetFocus`.

## Titles: use a token, not the whole title

A live session's tab is `CTO #<sid> (<topic>)`; the topic is added and changed by Claude
Code, and a worker tab starts with an animated glyph. So the request names `#<sid>` and
`wake.ps1` runs with `-Contains` (token of at least 6 characters, and it must match exactly
one tab). Consequence: an **ephemeral** session started with `-TabTitle "CMO ephemeral"`
has no sid in its title and cannot be woken this way (`woke: False`, "no tab matches").

## The request folder is a trust boundary

Whoever can write `state\wake\requests\*.json` can make the runner type a line + Enter
into a tab. So the runner is not a "type this" service: it accepts one marker shape,
`[New message from <LABEL>]` (label `[A-Za-z0-9_.#-]{1,40}`), a title from
`[A-Za-z0-9_.# -]{1,80}`, and drops requests older than 120 s. Values reach `wake.ps1` as
array arguments, never as code. The Python side refuses anything outside the same
alphabets before it writes a file.

## Known limits (not measured, or open)

- **Only tested against a `Read-Host` prompt in a tab of its own**, never a live Claude Code
  composer. `SendKeys` sends key events (not a paste), so Enter should submit, but that is
  unproven; the org's tmux path sends a rescue Enter because of a bracketed-paste swallow
  (GH #70).
- **It cannot tell that a person is typing.** The tab it wakes is raised to the front, and
  if a draft is sitting in that composer the marker is appended to it and submitted. If
  that is unacceptable on a desktop the CEO is using, add an idle check (`GetLastInputInfo`,
  refuse with a new exit code when the last input is a few seconds old) before enabling
  the wiring. Not built: it is a policy choice.
- **The session-0 hop was not measured from a real ssh shell** (see the report). The
  persistent-task design avoids the question: ssh only writes a file and runs an existing task.
- Blocks the caller up to 15 s (`_WAKE_WAIT_S`) waiting for the result; typical 4 s.

## Wiring (done in task-49f70bc6, OFF by default)

`tools/node_dispatch.py` `_windows_wake`, called from the win32 branch of
`_write_clevel_letter`. The wake runs only when the environment variable `ORG_WIN_WAKE`
is exactly `1`. Otherwise the answer is the W3.3 one, `woke: false`, and
`wake_windows_tab` is not called. With the flag on, the letter is written first, then
`wake_windows_tab(f"{role}-{sid}", from_role.upper())` is called once, and its `woke`
and `why` come back in the verb's result. A wake that returns false or raises never
fails the delivery. Worker letters (`_append_worker_mailbox`) stay `woke: false`: a
worker reads `MAILBOX.md` before every tool call and needs no nudge. The flag stays off
until the CEO decides the question in "Decision for the CEO" (a wake raises a window and
presses Enter). Details: `docs/ops/node-dispatch.md`, pinned by `tests/test_w35_wire.py`.
