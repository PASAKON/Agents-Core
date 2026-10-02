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
| `probe` | none | reports host, os, free GB, running workers, git version, `provides_measured` and `probe_errors` (below); writes the probe fields of this host's `hosts` row |
| `pid_alive` | `task-xxxxxxxx` | is the pid recorded on this host's task alive (`alive` true/false) |
| `spawn_worker` | `task-xxxxxxxx` | starts the worker for a pending task whose `host` is this host (a NULL host is refused on every OS), through `delegate_task` |
| `kill_worker` | `task-xxxxxxxx` | `worker_reap.close_dev`; keeps its own "only review/done" refusal rules |
| `start_clevel` | `<role> [--resume <8 hex>]` | starts a C-level session; role must be in `policies/agents.yaml` `c_level`; refused (exit 2) when 3 sessions of that role are already live on this host or another start of that role is still running or succeeded less than 60 s ago |
| `deliver_letter` | `<digits, max 12>` | writes hub letter N into this host's mailbox, wakes the pane, marks it delivered; a call that overlaps one still writing is refused (exit 2) |
| `publish_branch` | `task-xxxxxxxx` | `git push origin <the task's own branch>` from its worktree, never force |

Patterns: task id `task-[0-9a-f]{8}`, session id `[0-9a-f]{8}`, branch
`agent/[a-z_]+-task-[0-9a-f]{8}`.

### probe: `provides_measured` and `probe_errors` (W4.4)

`probe` looks at the box and reports what it can do, instead of trusting
`config/hosts.yaml`. `provides_measured` is a list of names, always starting with the
OS family. It is reported in the reply only: it is **not** written to the `hosts` row,
and `lib/router.py` does not read it yet.

| name | true when |
|---|---|
| `macos` / `linux` / `windows` | the OS family (exactly one, always first) |
| `chrome` | a Chrome or Chromium binary is a regular file at the usual place: `/Applications` and `~/Applications` (macOS); `google-chrome`, `chromium` and similar on PATH, `/opt/google/chrome/chrome`, `/snap/bin/chromium` (Linux); `%PROGRAMFILES%`, `%PROGRAMFILES(X86)%`, `%LOCALAPPDATA%` (Windows) |
| `ffmpeg` | `ffmpeg` is on PATH and `ffmpeg -version` exits 0 within 5 s |
| `gpu` | `nvidia-smi -L` exits 0 within 5 s and lists a `GPU ` line. NVIDIA only: macOS Metal is not reported |
| `node20` | `node --version` exits 0 within 5 s and the major is 20 or more |
| `playwright_chromium` | the Playwright browsers folder holds a `chromium*` folder. Folder: `$PLAYWRIGHT_BROWSERS_PATH` (`0` means none), else `~/Library/Caches/ms-playwright` (macOS), `~/.cache/ms-playwright` (Linux), `%LOCALAPPDATA%\ms-playwright` (Windows) |
| `runner_claude` | Linux, Windows: `$CLAUDE_CONFIG_DIR/.credentials.json` (default `~/.claude/`) exists and is not empty. macOS: see below |
| `runner_codex` | `$CODEX_HOME/auth.json` (default `~/.codex/`) exists and is not empty |
| `runner_agy` | `~/.gemini/antigravity-cli/antigravity-oauth-token` exists and is not empty |

A runner name means "a credential file is there", read from `os.stat` (existence and
size). The file is never opened, read, hashed or printed. It does not say the login is
still valid, and it does not say the CLI is installed (`runners` lists the installed
ones).

**`runner_claude` on macOS.** Claude Code keeps the login in the Keychain, so the file
is not the test there. Two checks, in order, neither reads the secret:

1. `claude auth status --json` (when `claude` is on PATH): only its `loggedIn` boolean
   is used. The same output carries an email and an org name; they are parsed in place
   and never stored, logged or returned. `loggedIn` true or false is the answer.
2. If the CLI cannot answer (not on PATH, hung past 5 s, would not start, output that
   is not that JSON): `/usr/bin/security find-generic-password -s "Claude Code-credentials"`.
   Attributes only: **no `-w` and no `-g`**, which would print the password. The exit
   code is the whole answer (0 item present; any other exit, such as 44 not found,
   reads as absent), and stdout and stderr go to /dev/null.

With `CLAUDE_CONFIG_DIR` set, the default Keychain item may belong to a different
login (not measured here), so step 2 is skipped and the file check is used instead. `tests/test_mesh_followups.py` fails if a `-w` or `-g` style flag ever reaches
a child's argv or appears as a string in `tools/node_dispatch.py`.

Every detector is bounded and cannot fail the probe. A child is an argv list (no
shell), with stdin and stderr on /dev/null and a 5 s timeout (`PROBE_CHILD_TIMEOUT_S`),
so the worst case is 3 children, 15 s (5 children, 25 s on macOS, where `runner_claude`
may run `claude` and then `security`). A detector that raises or times out is left out
of `provides_measured` and adds one entry to `probe_errors`: `"<name>: <ExceptionType>"`,
the type only, never the message.

Names the node cannot measure (`macos_cu`, `blender_bridge`, `win_gui`, `always_on`,
`api`) stay declared in `hosts.yaml`.

## authorized_keys line

One line per dispatcher key on each host, installed by W2.8 (W2.2 and the W2.7
review touch no `authorized_keys`). The forced command is fixed text. sshd never
puts the caller's text on it; the caller's text arrives only as
`SSH_ORIGINAL_COMMAND`, which node_dispatch splits itself. Revised in W2.7
(task-42fdcda7, `docs/reports/task-42fdcda7/REPORT.md`):

    # Contabo (agents_root from config/hosts.yaml; the Mac's is /Users/gob/MoonieXHQ/Agents/Core)
    command="cd /opt/MoonieXHQ/Agents/Core && exec /bin/bash scripts/hub/with-org-db-env.sh /opt/MoonieXHQ/Agents/Core/.venv/bin/python -E -s -m tools.node_dispatch",from="<dispatcher tailnet IP>/32",restrict ssh-ed25519 AAAA... org_dispatch-<dispatcher>

    # winbox (W3.4, NOT installable yet, see below): no shell syntax, so the line means the same under cmd or PowerShell
    command="C:\Users\passg\mooniex\repo\MoonieX-Agents\.venv\Scripts\python.exe -E -s C:\Users\passg\mooniex\repo\MoonieX-Agents\tools\infisical_setup.py run Org-Node prod --as winbox -- C:\Users\passg\mooniex\repo\MoonieX-Agents\.venv\Scripts\python.exe -E -s C:\Users\passg\mooniex\repo\MoonieX-Agents\tools\node_dispatch.py",from="<dispatcher tailnet IP>/32",restrict ssh-ed25519 AAAA... org_dispatch-<dispatcher>

- **The forced command reaches the hub through a wrapper (G1, 2026-10-02).**
  Since the G1 cutover the ledger is the Postgres hub and `state/tasks.db` is a
  tombstone. sshd starts the forced command with a bare environment (no
  `ORG_DB_URL`; `restrict` and `PermitUserEnvironment no` keep it that way), so
  a line that starts python directly reaches the tombstone, and every verb that
  touches the ledger fails (`probe` included). On a POSIX host the line starts
  node_dispatch through `scripts/hub/with-org-db-env.sh`, as
  `deploy/systemd/org-snapshot.service` does: the wrapper sources
  `~/.config/mooniex/org-db.env`, and when that holds no `ORG_DB_URL` (Contabo)
  it runs the command under `tools/infisical_setup.py run Agents-Core prod`
  with the identity named by `~/.config/mooniex/node.yaml` (`host: contabo`,
  `/etc/infisical/contabo.env`). The wrapper never reads `SSH_ORIGINAL_COMMAND`;
  it passes the environment on, so node_dispatch still finds it.
- winbox: the checkout is `config/projects.yaml` `paths.winbox`
  (`C:\Users\passg\mooniex\repo\MoonieX-Agents`). `agents_root` in
  config/hosts.yaml is the spawn directory beside it, which has no `.venv` and
  no `tools`. The wrapper is bash (`org_db_wrapper` skips Windows), so winbox
  reaches the hub the way `deploy/join/join.ps1` runs its probe: through
  `tools\infisical_setup.py run Org-Node prod --as winbox`. That needs winbox's
  Org-Node identity (W3), and the line is **not verified on winbox**. Install
  it only after `infisical_setup.py run Org-Node prod --as winbox -- <python> -m
  tools.node_dispatch probe` answers `"ok": true` on the box itself.

- `restrict` turns on every restriction sshd knows: no port, agent or X11
  forwarding, no pty, no `~/.ssh/rc`, and any restriction a later OpenSSH adds
  (sshd(8), AUTHORIZED_KEYS FILE FORMAT; checked against OpenSSH_9.4p1 on the Mac).
- `from=` is a pattern list of source addresses. Pin it to the dispatcher's own
  tailnet address, not `100.64.0.0/10`: every device on the tailnet (phones,
  shared nodes) is inside that range. Use one key per dispatcher
  (`org_dispatch-mac`, `org_dispatch-contabo`) so `from=` can be exact and one
  leaked key is revoked alone. On disk every dispatcher keeps its own key at
  `~/.ssh/org_dispatch` (the path lib/mesh.py reads and deploy/join/join.sh
  writes); `org_dispatch-<dispatcher>` is the key's comment, which names it here.
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
- The Mac: until gate G2 its sshd stays closed, and this key is for local
  tests only. At G2 the CEO turns on Remote Login on the tailnet, after
  `docs/ops/mac-sshd-hardening.md` (CEO decision 2026-09-28, design §6
  decision 1; recorded in org ADR 0034, which supersedes "the Mac keeps sshd
  closed").

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
dispatcher's `known_hosts`, under the address in `mesh_ssh` (below), not under
an admin alias: W2.8 records it first, from the fingerprint the target's own
`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` prints over the admin
channel, or every call is MeshUnreachable.

**No ssh config (W2.8).** `IdentitiesOnly` does not drop the `IdentityFile`
lines a config file names for the destination (the admin alias's own line, or a
`Host *` default), so the admin key would still be offered when `org_dispatch`
is refused, and W2.8 check 1 could pass with the forced command missing. A mesh
call therefore reads no config file at all: `lib/mesh.build_argv` runs
`ssh -F none` (`MESH_SSH_CONFIG`), which skips `~/.ssh/config` and
`/etc/ssh/ssh_config`, so on every dispatcher the dispatch key is the only
identity ssh has, whatever that machine's config says.

With no config there is no alias to resolve. The destination is the host's
`mesh_ssh` in `config/hosts.yaml`, `user@<tailnet address>`: contabo
`root@100.118.171.23`, winbox `passg@100.124.196.11`, mac `null` until G2. It
must be the tailnet address: `from=` pins the dispatcher's tailnet address, and
the admin alias `mooniex-vps` dials Contabo's public one. A host without
`mesh_ssh`, or with a value that is not a plain `user@address`, is never dialled
(`MeshUnreachable`; `tests/test_w28_mesh_destination.py`). A joined node's entry
has no `mesh_ssh` until someone adds its tailnet address.

The admin aliases (`ssh:` in hosts.yaml: `mooniex-vps`, `winbox`) stay as they
are, for people and for the admin readers (watchdog heartbeat, branch_poller,
delegate's remote spawn and disk check, worker_reap, quota, mesh_check). The
W2.7 review first proposed a `<host>-mesh` Host block per target on each
dispatcher. `-F none` replaced it: a Host block cannot rule out a `Host *`
IdentityFile, and it needs one block per target on every dispatcher.

**Tailscale SSH must be off on every target** (`tailscale set --ssh=false`;
`tailscale debug prefs` shows `"RunSSH": false`). With it on, tailscaled answers
port 22 on the tailnet address itself and applies the tailnet policy instead of
`authorized_keys`, so the forced command is never involved. Check 2 below
catches it: a shell answers `probe; id`.

**Retry cap for an unanswered spawn.** A `spawn_worker` the host did not answer leaves
the row `queued_remote`, and the watchdog dials it again once per pass (300 s). Each
unanswered attempt writes one `status_queued_remote` event, counted in the ledger per
task (`delegate._queued_remote_attempts`). At `lib/mesh.max_attempts()` attempts the
next pass does not dial: `delegate.give_up_queued_remote` moves the row to `failed`
(its `delegate_log` names the host and the count), which releases its path locks
exactly as a failed launcher run does, and sends the owner one letter. Default 12
(`lib/mesh.MAX_ATTEMPTS`): the first attempt is at delegate time, so that is 11 passes,
about 55 minutes of silence, long enough for a reboot or a Windows update restart and
short enough that the locks do not block other work for hours. Override with
`ORG_MESH_MAX_ATTEMPTS` in the watchdog's environment; a value that is not a whole
number of 1 or more is ignored, never read as "no cap". A row already moved by the far
side, or failed by another watchdog, is neither failed again nor announced again.

**`deliver_letter` timeout.** On a Windows host with `ORG_WIN_WAKE=1` the verb also
wakes the C-level tab (`agent_transport.wake_windows_tab`: `schtasks /run`, then a wait
for the result), which can block `agent_transport.WAKE_WORST_CASE_S` (30 s). The letter
is already on disk by then, so a slow wake must not read as an unreachable host. The
verb's timeout in `lib/mesh.VERB_TIMEOUT_S` is the ssh connect time, plus that constant
(imported, not copied), plus `LETTER_WRITE_MARGIN_S`: 10 + 30 + 15 = 55 s, instead of the
30 s default.

### W2.8 acceptance checks, once per host after the key is installed

From the dispatcher, with only the dispatch key, exactly as lib/mesh.py dials
(`K="-F none -i ~/.ssh/org_dispatch -o BatchMode=yes -o IdentitiesOnly=yes -o IdentityAgent=none -o StrictHostKeyChecking=yes"`,
`D` = the host's `mesh_ssh`):

1. `ssh $K $D probe` prints one JSON line with `"ok": true` and this host's name.
2. Each of `'probe; id'`, `'probe && id'`, `'$(id)'`, `` '`id`' ``, `'probe | id'`
   returns `"ok": false`, exit 2, and no `uid=` anywhere in the output.
3. `ssh $K -N -L 12345:127.0.0.1:22 $D`, then a connection to local port 12345,
   is refused (`administratively prohibited`).
4. `ssh $K -t $D probe` reports that no pty was allocated and still returns the JSON line.
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
counts the live `state/locks/<role>-<sid>.lock` files under a `locks` row
`clevel:<host>:<role>:start`, so two overlapping starts cannot both pass the
count; a start that succeeds keeps the row 60 s, because the launcher writes its
lock file only after the verb returns).

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
`<worktree>\MAILBOX.md`. Every value that
reaches PowerShell is checked against an allow-list first; a refusal is exit 2 with
no subprocess run. Since W2.7, `spawn_worker` on Windows needs the row's host to be
this host and re-checks, read-only, what the hub's `delegate_task` gated
(dependencies finished, no touches overlap with a task in flight, and the disk floor,
below), and the `MAILBOX.md` append refuses a symlink or hard link.

**Disk floor on Windows (W2.7 F3b).** Before any PowerShell, `spawn_worker` refuses
(exit 2, `disk red on <host>: <free> GB free < <floor> GB floor`) when free space on the
drive that holds the worktrees root is below the floor. It uses `tools/delegate.py`'s
own pieces, not copies: the reading seam `delegate._free_gb`, the floor
`delegate._disk_orange_floor_gb()` (key `gauge.orange` of `config/storage-policy.yaml`,
a strict `<`), and the `scope.disk_floor` rule (an owner outside the scope is not
gated). A worktrees root that does not exist yet is measured at its nearest existing
parent. A free-space read that fails is a refusal. The row stays `pending`: queueing it
for disk is the hub's job (`delegate_task` does it on the normal path). The
browser-operator cap is still the hub's alone.

**Waking a C-level tab on Windows (W3.5), off by default.** `deliver_letter` to a
C-level session on Windows writes the mailbox and answers `"woke": false`, and
`agent_transport.wake_windows_tab` is not called. With the environment variable
`ORG_WIN_WAKE=1` (exactly `1`; `true`, `yes`, ` 1` and every other value stay off) it
calls `wake_windows_tab("<role>-<sid>", "<FROM ROLE>")` after the letter is on disk and
returns its answer as `woke` plus `why`. A wake that fails or raises is `"woke": false`
with a `why`; the letter stays delivered. A worker letter (`MAILBOX.md`) is never woken.
The flag is off because a wake raises a window on the desktop and presses Enter, and
the CEO has not decided that is acceptable (`docs/ops/windows-wake.md`, "Decision for
the CEO"). The variable must be in the environment of the process sshd starts for the
forced command, so on winbox it is a machine-level variable plus an sshd restart
(not tried here). A wake blocks the verb for up to about 30 s in the worst case
(`schtasks` 15 s, then a 15 s wait for the result); typical is 4 s.

**Waking on the Mac and Contabo (task-f9d23d0b).** `deliver_letter` for a worker or a
C-level session on a POSIX host writes the mailbox, nudges the tmux pane
(`agent_transport.attempt_wake`), and answers `"woke": true` only when the keys reached a
live tmux session and every tmux call exited 0. Otherwise it answers `"woke": false` plus
a `why`. The letter stays delivered either way. `mesh_check` L5 reads `woke`
(`docs/ops/mesh-check.md`).

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

Tests: `.venv/bin/python -m pytest tests/test_node_dispatch.py tests/test_w27_security.py
tests/test_w44_probe_provides.py tests/test_w35_wire.py`
