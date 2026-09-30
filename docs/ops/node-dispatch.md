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
| `spawn_worker` | `task-xxxxxxxx` | starts the worker for a pending task whose `host` is this host (a NULL host is refused on every OS), through `delegate_task` |
| `kill_worker` | `task-xxxxxxxx` | `worker_reap.close_dev`; keeps its own "only review/done" refusal rules |
| `start_clevel` | `<role> [--resume <8 hex>]` | starts a C-level session; role must be in `policies/agents.yaml` `c_level`; refused (exit 2) when 3 sessions of that role are already live on this host or another start of that role is still running |
| `deliver_letter` | `<digits, max 12>` | writes hub letter N into this host's mailbox, wakes the pane, marks it delivered; a call that overlaps one still writing is refused (exit 2) |
| `publish_branch` | `task-xxxxxxxx` | `git push origin <the task's own branch>` from its worktree, never force |

Patterns: task id `task-[0-9a-f]{8}`, session id `[0-9a-f]{8}`, branch
`agent/[a-z_]+-task-[0-9a-f]{8}`.

## authorized_keys line

One line per dispatcher key on each host, installed by W2.8 (W2.2 and the W2.7
review touch no `authorized_keys`). The forced command is fixed text. sshd never
puts the caller's text on it; the caller's text arrives only as
`SSH_ORIGINAL_COMMAND`, which node_dispatch splits itself. Revised in W2.7
(task-42fdcda7, `docs/reports/task-42fdcda7/REPORT.md`):

    # Mac / Contabo (agents_root from config/hosts.yaml; Contabo = /opt/MoonieXHQ/Agents/Core)
    command="cd /Users/gob/MoonieXHQ/Agents/Core && exec .venv/bin/python -E -s -m tools.node_dispatch",from="<dispatcher tailnet IP>/32",restrict ssh-ed25519 AAAA... org_dispatch-<dispatcher>

    # winbox: no shell syntax, so the line means the same under cmd or PowerShell
    command="C:\Users\passg\mooniex\.venv\Scripts\python.exe -E -s C:\Users\passg\mooniex\tools\node_dispatch.py",from="<dispatcher tailnet IP>/32",restrict ssh-ed25519 AAAA... org_dispatch-<dispatcher>

- `restrict` turns on every restriction sshd knows: no port, agent or X11
  forwarding, no pty, no `~/.ssh/rc`, and any restriction a later OpenSSH adds
  (sshd(8), AUTHORIZED_KEYS FILE FORMAT; checked against OpenSSH_9.4p1 on the Mac).
- `from=` is a pattern list of source addresses. Pin it to the dispatcher's own
  tailnet address, not `100.64.0.0/10`: every device on the tailnet (phones,
  shared nodes) is inside that range. Use one key per dispatcher
  (`org_dispatch-mac`, `org_dispatch-contabo`) so `from=` can be exact and one
  leaked key is revoked alone.
- `-E -s`: Python ignores `PYTHON*` variables and the user site-packages.
  `restrict` and the default `PermitUserEnvironment no` already stop a caller
  from setting variables; macOS still accepts `LANG` and `LC_*` (`AcceptEnv` in
  `/etc/ssh/sshd_config.d/100-macos.conf`), which Python does not execute.
- POSIX: sshd runs the forced command through the account's shell (`$SHELL -c`),
  so that shell's non-interactive startup file runs first (zsh `~/.zshenv`, bash
  `$BASH_ENV`). Keep it free of anything that reads `SSH_ORIGINAL_COMMAND`.
- Windows, the old line `command="cmd /c cd /d ... && ..."`: Win32-OpenSSH runs a
  forced command through its DefaultShell, `cmd.exe /c <command>` unless
  `HKLM\SOFTWARE\OpenSSH\DefaultShell` names another shell. That outer cmd
  parses the `&&` itself: the inner `cmd /c cd /d ...` changes only its own
  directory and exits, and python starts in the profile directory, where
  `-m tools.node_dispatch` cannot import. The old line fails closed (no JSON
  line, so the caller sees MeshUnreachable) and never works. A caller cannot
  steer it: the text holds no reference to `SSH_ORIGINAL_COMMAND`. **Not
  verified on winbox** (no Windows box was reachable from the review). The new
  line needs no `cd`: node_dispatch puts its own repo root on `sys.path`
  (verified on the Mac from another working directory, W2.7).
- Windows: an Administrators-group account reads
  `C:\ProgramData\ssh\administrators_authorized_keys` (`Match Group
  administrators` in the default `sshd_config`), not `~\.ssh\authorized_keys`,
  and sshd ignores that file unless only Administrators and SYSTEM can write it.
  Win32-OpenSSH parses key options with the portable OpenSSH code, so
  `command=`, `from=` and `restrict` apply. Whether `restrict`'s no-pty holds
  exactly under ConPTY is **not verified**.
- Mac sshd stays closed (design §6): on the Mac this key is for local tests and a
  later pull-side caller, not an open door. If it is ever opened, apply
  `docs/ops/mac-sshd-hardening.md` first.

### Client side (lib/mesh.py)

`ssh` reads `~/.ssh/config` for the alias. A `ControlMaster`/`ControlPath` entry
for `mooniex-vps` or `winbox` would make a mesh call ride an admin connection
that is already open: the verb then runs as a plain command under the admin key,
and the forced command is never involved. Agent keys would also be offered when
the far side refuses `org_dispatch`. Since W2.7 (F4) `lib/mesh.SSH_OPTIONS` puts
these on every mesh call:

    -o BatchMode=yes -o ConnectTimeout=10 -o IdentitiesOnly=yes -o IdentityAgent=none
    -o ControlMaster=no -o ControlPath=none -o ForwardAgent=no -o ForwardX11=no
    -o ClearAllForwardings=yes -o PermitLocalCommand=no -o StrictHostKeyChecking=yes

`StrictHostKeyChecking=yes` means the far host's key must already be in the
dispatcher's `known_hosts`: W2.8 records it first, or every call is
MeshUnreachable.

**Dedicated alias (W2.8).** `IdentitiesOnly` does not drop `IdentityFile` lines
the config names for that alias, so the admin key is still tried when
`org_dispatch` is refused, and W2.8 check 1 could pass with the forced command
missing. Give the mesh its own alias per host, `<host>-mesh`, whose only identity
is the dispatch key. `config/hosts.yaml` `ssh:` cannot simply point at it: the
admin readers (watchdog heartbeat, branch_poller, delegate's remote spawn and
disk check, worker_reap, quota, mesh_check) read the same field and need the
admin key. W2.8 adds a separate field (e.g. `mesh_ssh: contabo-mesh`) and
`lib/mesh.build_argv` reads it; that is a code change for W2.8, not made here.
The alias itself, on each dispatcher:

    Host contabo-mesh
        HostName <contabo tailnet IP>
        User root
        IdentityFile ~/.ssh/org_dispatch-<dispatcher>
        IdentitiesOnly yes
        ControlMaster no
        ControlPath none

Keep the admin alias (`mooniex-vps`, `winbox`) for people and the watchdog; never
put the admin key under a `-mesh` alias.

### W2.8 acceptance checks, once per host after the key is installed

From the dispatcher, with only the dispatch key
(`K="-i ~/.ssh/org_dispatch-<dispatcher> -o IdentitiesOnly=yes -o IdentityAgent=none -o ControlPath=none"`):

1. `ssh $K <alias> probe` prints one JSON line with `"ok": true` and this host's name.
2. Each of `'probe; id'`, `'probe && id'`, `'$(id)'`, `` '`id`' ``, `'probe | id'`
   returns `"ok": false`, exit 2, and no `uid=` anywhere in the output.
3. `ssh $K -N -L 12345:127.0.0.1:22 <alias>`, then a connection to local port 12345,
   is refused (`administratively prohibited`).
4. `ssh $K -t <alias> probe` reports that no pty was allocated and still returns the JSON line.
5. From a tailnet address outside `from=`: `Permission denied (publickey)`.
6. On the host, the newest `events` rows are `actor=node_dispatch` with `caller`
   set to the dispatcher's tailnet address.
7. winbox only: `reg query HKLM\SOFTWARE\OpenSSH /v DefaultShell` (record which
   shell runs the forced command), `icacls C:\ProgramData\ssh\administrators_authorized_keys`
   (Administrators and SYSTEM only), and step 1 returns `"os": "windows"`.

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
and writes nothing, and a call that overlaps one still writing is refused: each
delivery holds a `locks` row `letter:<id>:delivery` for up to 120 s); open more
than 3 live sessions of one C-level role on one host (W2.7 F10: `start_clevel`
counts the live `state/locks/<role>-<sid>.lock` files, and holds a `locks` row
`clevel:<host>:<role>:start` for up to 300 s so two overlapping starts cannot
both pass the count).

The relay's `spawn_c_level` (runners/relay_mcp_server.py) also allows at most 3
spawn attempts that pass its checks per 10 minutes per relay process (a call it
rejects first takes no slot; a 4th answers `rate_limited` with `retry_after_s`). The relay is one stdio
process per caller session; the secretary starts one per `claude -p` turn, so
there the limit is per turn and the node-side cap above is the durable bound.

On Windows (W3.3) every verb runs in place: `pid_alive` uses `lib.proc`, `spawn_worker`
runs `windows/spawn-worker.ps1` from the checkout (which makes its own interactive
one-shot scheduled task), `start_clevel` registers one for `windows/cxo-claude.ps1`
(the id is passed as `-Session`, so there is no `<role>-active` pointer and a letter
names the session by `to_session`), and `deliver_letter` writes the inbox or
`<worktree>\MAILBOX.md` without waking anything (`woke: false`). Every value that
reaches PowerShell is checked against an allow-list first; a refusal is exit 2 with
no subprocess run. Since W2.7, `spawn_worker` on Windows needs the row's host to be
this host and re-checks, read-only, what the hub's `delegate_task` gated
(dependencies finished, no touches overlap with a task in flight), and the
`MAILBOX.md` append refuses a symlink or hard link.

## Audit

Every call, refusals included, writes one `events` row: `actor=node_dispatch`,
`kind=dispatch`, payload `{verb, args, caller, ok, error}`. `caller` is the address
from `SSH_CLIENT` (checked to be an IP shape, else null). An unparseable command logs
`raw` truncated to 256 chars. A failed audit write never changes the result.
`error`, `raw` and `letters.last_error` pass through a credential redactor first
(URL userinfo, GitHub and `sk-` tokens, bearer values), because a failing child
such as `git push` can print its remote URL with a token in it.

In-process use (W2.3): `dispatch(verb, args) -> dict`. It is synchronous; call it
through `asyncio.to_thread` from async code.

Tests: `.venv/bin/python -m pytest tests/test_node_dispatch.py tests/test_w27_security.py`
