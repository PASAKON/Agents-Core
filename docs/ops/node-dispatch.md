# node_dispatch — the one command an `org_dispatch` key may run

`tools/node_dispatch.py` (Org Mesh W2.2, `docs/design/org-mesh.md`). sshd runs it
as the forced command of a dedicated key. The caller's text arrives in
`SSH_ORIGINAL_COMMAND`, is split with `shlex.split`, and is matched against a fixed
verb table. It is never handed to a shell. A caller can **name** a hub row (a task
id, a letter id). It cannot **send** a command.

## Verbs

Exactly these seven. Anything else is refused. Argument patterns are `fullmatch`.

| verb | args | does |
|---|---|---|
| `probe` | none | reports host, os, free GB, running workers, git version; writes the probe fields of this host's `hosts` row |
| `pid_alive` | `task-xxxxxxxx` | is the pid recorded on this host's task alive (`alive` true/false) |
| `spawn_worker` | `task-xxxxxxxx` | starts the worker for a pending task on this host, through `delegate_task` |
| `kill_worker` | `task-xxxxxxxx` | `worker_reap.close_dev`; keeps its own "only review/done" refusal rules |
| `start_clevel` | `<role> [--resume <8 hex>]` | starts a C-level session; role must be in `policies/agents.yaml` `c_level` |
| `deliver_letter` | `<digits, max 12>` | writes hub letter N into this host's mailbox, wakes the pane, marks it delivered |
| `publish_branch` | `task-xxxxxxxx` | `git push origin <the task's own branch>` from its worktree, never force |

Patterns: task id `task-[0-9a-f]{8}`, session id `[0-9a-f]{8}`, branch
`agent/[a-z_]+-task-[0-9a-f]{8}`.

## authorized_keys line

One line, installed by W2.8 (this task does not touch any `authorized_keys`).
`cd` is required: `-m tools.node_dispatch` only imports from the repo root.

    # Mac / Contabo (agents_root from config/hosts.yaml; Contabo = /opt/MoonieXHQ/Agents/Core)
    command="cd /Users/gob/MoonieXHQ/Agents/Core && exec .venv/bin/python -m tools.node_dispatch",from="100.64.0.0/10",restrict ssh-ed25519 AAAA... org_dispatch

    # winbox (UNVERIFIED: default shell is cmd; confirm in W2.8 before relying on it)
    command="cmd /c cd /d C:\Users\passg\mooniex && .venv\Scripts\python.exe -m tools.node_dispatch",from="100.64.0.0/10",restrict ssh-ed25519 AAAA... org_dispatch

- `from="100.64.0.0/10"` limits the key to the tailnet. `restrict` turns off pty,
  port, agent and X11 forwarding.
- On Windows an Administrators-group user reads
  `C:\ProgramData\ssh\administrators_authorized_keys`, not `~\.ssh\authorized_keys`.
- Mac sshd stays closed (design §6): on the Mac this key is for local tests and a
  later pull-side caller, not an open door.

## Output and exit codes

stdout is exactly one ASCII JSON line, nothing else (fd 1 is pointed at stderr for
the duration of the verb, so a noisy backend cannot corrupt it).

    {"ok":true,"verb":"pid_alive","result":{"task_id":"task-1234abcd","pid":4242,"alive":true}}
    {"ok":false,"verb":"pid_alive","error":"task task-1234abcd is on host 'winbox', this host is 'mac'"}

| exit | meaning |
|---|---|
| 0 | ok |
| 1 | the verb ran and failed (push rejected, no live session, backend raised) |
| 2 | refused: unknown verb, wrong arg count, pattern miss, >256 chars, NUL or newline, wrong host, wrong status. Nothing ran |

## What a caller can and cannot do

Can: query liveness of a task's pid on this host, start/stop the worker of a hub
task assigned to this host, start a C-level from the allow-list, deliver a
hub letter addressed to this host once, push one task branch.

Cannot: run a shell or any binary of its choosing; name a path, a branch, a role or
a host of its own; push `main`, force-push or delete; act on another host's task or
letter; touch a letter twice (`deliver_letter` again returns `already_delivered`
and writes nothing); on Windows, `pid_alive` and `start_clevel` are refused until W3.

## Audit

Every call, refusals included, writes one `events` row: `actor=node_dispatch`,
`kind=dispatch`, payload `{verb, args, caller, ok, error}`. `caller` is the address
from `SSH_CLIENT` (checked to be an IP shape, else null). An unparseable command logs
`raw` truncated to 256 chars. A failed audit write never changes the result.

In-process use (W2.3): `dispatch(verb, args) -> dict`. It is synchronous; call it
through `asyncio.to_thread` from async code.

Tests: `.venv/bin/python -m pytest tests/test_node_dispatch.py`
