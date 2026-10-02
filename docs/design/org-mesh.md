# Org Mesh — every machine is a node, one hub, pull not push

Status: **DRAFT for CEO decision** · CTO (session e6754203) · 2026-09-28
Extends `multi-host-workers.md` (Phase 1 + 2 done) and absorbs its open Phase 3
(router) and Phase 4 (hub on Contabo, ADR 0025). Does not redesign git as the
artefact channel or the worker launchers — both stay.

CEO question (2026-09-28): can `spawn cxo` and `delegate worker` run on the Mac,
winbox and Contabo; can a worker be delegated across machines in every
direction; can the three machines ssh each other; and can a new machine register
and be used straight away?

## 1. Measured state (2026-09-28)

Live probes from the Mac session plus both task ledgers. "Last proof" is the
newest row that actually finished, not a code reading.

### 1a. SSH (probed today, BatchMode, 8 s timeout)

| from \ to | Mac | Contabo | winbox |
|---|---|---|---|
| **Mac** | — | ok | ok |
| **Contabo** | refused (port 22 closed) | no self alias | ok |
| **winbox** | refused (`TcpTestSucceeded False`) | ok (public IP and tailnet) | — |

The Mac's closed sshd is deliberate: `runners/mac_agent.py` docstring — "the Mac
dials out ... that asymmetry is the security design, not a gap to fix".

### 1b. Start a C-level session

| host | CTO | CXO (CMO/CFO/CGO) | org MCP in the session |
|---|---|---|---|
| Mac | ok (`spawn-cto.sh`) | ok (`spawn-cxo.sh`) | yes |
| Contabo | ok (Console / relay `spawn_c_level`) | ok (same) | yes |
| winbox | standalone only (`windows/win-cto.ps1`) | **no launcher** | **no** (`roles/cto-windows.md`) |

Contabo launchers label the machine by testing `/opt/mooniex-agents`
(`scripts/cto-claude.sh:221`). That compat link is due for removal ~2026-10-01;
after that the label becomes the hostname (`VMI3371421`) and session rows split.

### 1c. Delegate a worker

| from \ to | Mac | Contabo | winbox |
|---|---|---|---|
| **Mac** | ok | spawn ok, last proof 2026-09-25 (6 done) | wired, last proof 2026-09-22 (44 done); 1 fail 09-23 "claude did not appear within 60s"; **not tried since the 09-24 reset** |
| **Contabo** | **no path** | **broken** — task-cf5db03d 2026-09-28 01:50 `Could not resolve hostname mooniex-vps` | spawn ok (7 done, last 09-23), **merge by hand** — `merge_task` needs the Mac path (task-854cb512) |
| **winbox** | no | no | no — no org MCP, no ledger |

Return channel for a remote worker (all hubbed on the Mac):

| piece | winbox worker | Contabo worker |
|---|---|---|
| branch + REPORT.md push | ok | ok |
| `branch_poller` flips to review | **off** (watchdog runs it only when `ORG_WATCHDOG_BRANCH_POLL=1`; the plist does not set it) | off |
| liveness (`remote_pid_alive`) | ok (`tasklist`) | **never detects death** — Windows-only command (`runners/branch_poller.py:187`) |
| `send_to_worker` | ok | **NotImplementedError** (`tools/send_to_worker.py:153`) |
| `merge_task` | Mac only | Mac only |

### 1d. Shared state

- Every host keeps its own `state/tasks.db`. A task created on Contabo is
  invisible on the Mac and the reverse. The Postgres hub (`ORG_DB_URL`, ADR 0025)
  is coded and not live.
- C-level letters cross no machine. Mac↔Contabo only through the secretary's
  `relay_queue`; nothing reaches winbox.

### 1e. Register a new machine

No pipe. Adding a host is about ten hand steps: ssh keys on every other box,
`~/.ssh/config` on the Mac, Tailscale join, clone, `claude` login, rows in
`hosts.yaml`, `projects.yaml` (`paths.<host>` per project), `machine-contract.yaml`,
secrets by hand. The only automated step is the worker launcher, which copies
itself on the first `delegate_task(host=...)`. 134 quoted host literals sit in 30
non-test files; `scripts/spawn-worker-remote.sh:296` hardcodes
`ORG_HOST=contabo`, so a second Linux box would identify as Contabo. Infisical's
free tier is full (5 of 5 identities).

## 2. Why it breaks — five root causes

1. **Mac-centric defaults.** `delegate_task` host defaults to `'mac'`
   (`tools/delegate.py:1536`); worktree, merge and poller read `proj["path"]`,
   the Mac path. Any host that is not the Mac hits Mac paths.
2. **No self-identity.** C-level sessions never know which host they are on, so
   Contabo delegating to `contabo` ssh's to itself through an alias it lacks.
3. **Push over ssh.** The spawner must reach INTO the target. That fails for the
   Mac (closed by design), fights Windows session 0 (needs a scheduled task in
   the desktop session) and makes liveness an ssh round trip per OS.
4. **One ledger per host.** Nothing is shared, so delegation, review and
   messaging can only work from the machine that holds the row.
5. **Registry by hand.** YAML edits plus host names in code; no join flow.

## 3. Design

### Principles

- **Pull, not push.** Every host runs one small `node_agent` that dials the hub
  and claims its own work. Nobody needs inbound access to anybody. This is the
  pattern `mac_agent.py` already uses for the secretary queue — generalised.
- **One ledger.** Postgres on Contabo over the tailnet (ADR 0025, already coded).
- **A host knows its own name** from a file, never from a path or hostname guess.
- **SSH stays for admin and fallback only.** Delegation does not depend on it.
- **Git stays the artefact channel.** Branch + REPORT.md, unchanged.

### Components

| # | component | what it does | builds on |
|---|---|---|---|
| C1 | Host identity | `~/.config/mooniex/node.yaml` `{host, hq_root}`; `lib.config.self_host()`; every launcher exports `ORG_HOST` from it. `delegate_task` default host = self; target == self → local launcher for this OS, never ssh. | `worker_init.current_host()` |
| C2 | Hub ledger | All org MCP servers set `ORG_DB_URL` → Contabo Postgres on its tailnet IP (not public). Tasks, locks, sessions, heartbeats, letters in one place. | `lib/db_pg.py`, `scripts/hub/*`, ADR 0025 |
| C3 | `node_agent` | One per host: launchd (Mac), systemd (Linux), Task Scheduler at logon in the desktop session (Windows). Each tick: write heartbeat (free disk, RAM, running workers, runners, provides); claim `tasks WHERE host = self AND status = 'queued' FOR UPDATE SKIP LOCKED`; spawn with the existing local launcher (`worker_init.py` / `spawn-worker-remote.sh` / `spawn-worker.ps1`); report pid liveness locally (no ssh `tasklist`); deliver letters; start C-level sessions on request. Fixed dispatch table only — a hub row can ask, never command arbitrary shell. | `runners/mac_agent.py` |
| C4 | Hub mailbox | `letters(to_host, to_role, to_session, body, status)`. `send_to_cxo` / `send_to_worker` write a row; the target's `node_agent` writes the local `state/inbox` file and wakes the pane. Cross-host C-level mail, winbox included. | `lib/mailbox.py` |
| C5 | Merge anywhere | `merge_task` resolves the repo with `project_path_for_host(project, self_host())`; gate tests run in a fresh local worktree of the pushed branch. | `tools/git_ops.py` |
| C6 | `hq join` | Register a machine (below). | `contabo_restore.sh`, `winbox-bootstrap.ps1`, blueprints |
| C7 | Router | `create_task(needs=[chrome, gpu, win_gui])` → hub picks a host whose `provides` covers `needs`, heartbeat fresh, running < `max_workers`, lowest load. Explicit `host=` still wins. | `hosts.yaml provides` (declared, unread today) |

**Duty split on a shared ledger (W1.5, merged 1cf295b4).** Every row has one owner for each duty
(`tools/worker_reap.py`). `row_host = host or dispatcher_host or self` and `row_dispatcher =
dispatcher_host or self`. So a row with NULL `host` belongs to whoever dispatched it. That is
accepted: rows from before W0 carry no host, and their dispatcher is the only box that ran them.
LOCAL duties (reap, gc, work_watch) belong to the machine where `row_host == self`. REMOTE close
belongs to the dispatcher, where `row_host != self` and `row_dispatcher == self`. The branch poller
takes in_progress rows with `row_dispatcher == self`, and either `host != self` or a codex/agy runner.
Invariant for the soak: each remote row has exactly one poller.

### Registry moves into the hub

- `hosts` table in Postgres, seeded once from `config/hosts.yaml`; the YAML
  becomes a generated export for reading, not the source.
- Project paths by convention: `<hq_root>/Projects/<Brand>/<Suffix>` (the HQ
  layout, IRON §54) computed from the host's `hq_root`. `projects.yaml
  paths.<host>` only for exceptions. Removes most host literals over time.
- `provides` is probed by the node (OS, Chrome, GPU, ffmpeg, runners on PATH and
  signed in), not typed by hand.

### `hq join` — plugging in a new machine

1. CEO taps **Add machine** on the phone (Run Inbox card). Hub mints a one-time
   join token (15 min) and a Tailscale pre-auth key tagged `tag:org-node`.
2. On the new box, one command:
   `curl -fsSL https://terminal.mooniex.com/join.sh | sh -s <token>` (Mac/Linux)
   or `iwr https://terminal.mooniex.com/join.ps1 | iex` (Windows).
3. The script installs Tailscale (joins with the pre-auth key), git, Python,
   Node 22 and `claude`; creates an ssh key and a node key; clones HQ +
   Agents-Core into the standard `hq_root`; writes `node.yaml`; probes
   `provides`; posts `{host, os, pubkey, provides}` to the hub.
4. Hub inserts the `hosts` row as `pending_login`, pushes the new pubkey to the
   other nodes' `authorized_keys` through their `node_agent`s (admin ssh only),
   and installs `node_agent` as a service on the new box.
5. The one human step: `claude` login, sent to the CEO's phone through Ask
   Inbox / the login relay. Row flips to `ready`.
6. First heartbeat → the router can place work there. `hq leave <host>` revokes
   the node key and Tailscale key and removes the pubkey everywhere.

### Security

- Postgres listens on the tailnet only. A mesh key is accepted only from its
  dispatcher's own tailnet address (`from=` with a /32).
- One `org_dispatch` key per dispatcher, revoked by deleting one
  `authorized_keys` line.
- sshd runs `tools/node_dispatch.py` as that key's forced command: seven
  verbs, never a shell (`docs/ops/node-dispatch.md`).
- **Changed 2026-09-28 (CEO, §6 decision 1):** the Mac no longer keeps sshd
  closed. It turns on Remote Login on the tailnet at gate G2, after
  `docs/ops/mac-sshd-hardening.md`. ADR 0034 records the reversal and the
  threat model. Until G2 the Mac is reached only through the relay queue
  (`runners/mac_agent.py`).
- Every join is approved by a CEO tap; no silent registration.

## 4. Target matrix (after W0–W4)

Every cell in 1b and 1c becomes ok, including Contabo → Mac and anything from
winbox. ~~with the Mac's sshd still closed. SSH (1a) stays as measured —
delegation no longer needs it.~~ Changed by the CEO's 2026-09-28 decision (§6):
every host, the Mac included from gate G2, answers the `org_dispatch` key, and
only with node_dispatch.

The measured final matrix (`mesh_check --expect w5 --live`, one run from each
host) goes here when W5 runs.

## 5. Waves

| wave | scope | done when (checkable) | needs CEO |
|---|---|---|---|
| **W0** | C1 + C5 on today's per-host ledgers: `self_host()`, default host = self, Linux local spawn on Contabo, `paths.contabo` → `/opt/MoonieXHQ/...`, `ORG_HOST` from `node.yaml`, Linux `remote_pid_alive` + `send_to_worker`, host-aware `merge_task`, machine label from `node.yaml` not `/opt/mooniex-agents`. Must land **before the compat link is removed (~10-01)**. | From a Contabo CTO: `delegate_task(host=None)` spawns on Contabo and `merge_task` merges on Contabo; `delegate_task(host='winbox')` merges on Contabo with no hand merge. | no (code) |
| **W1** | C2 — ADR 0025 cutover to Postgres on Contabo. | A task created on the Mac returns from `get_task` on Contabo, and the reverse. | restart window for every live C-level session |
| **W2** | C3 + C4 on all three hosts. | Contabo CTO `delegate_task(host='mac')` spawns on the Mac with Mac sshd still closed; a letter Mac CTO → Contabo CMO arrives; a winbox worker heartbeat shows in the hub. | no |
| **W3** | winbox as a full node: org MCP (venv), `cxo-claude.ps1`. | A CMO started on winbox runs `create_task` successfully. | no |
| **W4** | C6 `hq join` + `hosts` table + probed `provides`. | A throwaway Linux VM joins with one command + one phone tap + `claude` login, receives a delegated worker within 15 min, then leaves with `hq leave`. | Infisical identity for new hosts (free tier full) |
| **W5** | C7 router by `needs`. | `create_task(needs=['win_gui'])` lands on winbox without `host=`. | no |

### Scope moves (plan of 2026-09-29, CEO update the same day)

The table above is the design of 2026-09-28. These moves change it:

- **W0:** "`delegate_task(host='winbox')` merges on Contabo" moved to W3.
  Linux `remote_pid_alive` / `send_to_worker` were dropped: the W2 dispatch
  verbs `pid_alive` and `deliver_letter` replace them.
- **W2:** the `node_agent` pull model (C3) became an ssh mesh with
  forced-command keys (§6 decision 1). C4 letters reach the target through
  the `deliver_letter` verb instead of a `node_agent` tick. The router (C7)
  moved from W5 into W2 (W2.6). Mac Remote Login and its sshd hardening
  (W2.0, W2.8b) moved to the very end, as gate G2. The W2 cell "with Mac sshd
  still closed" no longer applies.
- **W4:** runs last, on Infisical Free (decision 4).
- **W5:** the router is built in W2.6 and tested again in W3, so W5 is only
  the full acceptance run, `mesh_check --expect w5 --live`.

## 6. Decisions for the CEO (all four ruled by the CEO on 2026-09-28)

1. **Pull model + Mac sshd stays closed** (recommended) vs open Mac Remote Login
   on the tailnet for a plain ssh mesh. Opening it is faster but reverses the
   documented security design and still leaves Windows session 0 and sleep.
   **Ruled: open Remote Login on the tailnet**, with forced-command keys so
   no caller gets a shell (ADR 0034). The Mac side waits on gate G2.
2. **W1 restart window** — the hub cutover needs every live C-level session
   restarted once.
   **Ruled: yes.** It ran as gate G1 on 2026-10-02 (Mac 04:35, Contabo 04:56 TH).
3. **Contabo as the single hub** — one bill and one box; the 2026-09-16 payment
   reboot is the precedent. Mitigation: nightly `pg_dump` to Drive (drive_leg
   `state-db` pattern) and read-only fallback to local SQLite.
   **Ruled: yes** (ADR 0025). Both mitigations run since 2026-10-02, and a
   restore drill into a throwaway database passed
   (`docs/ops/machine-contract-drive-leg.md`).
4. **Secrets for new hosts** — Infisical free tier is 5 of 5; a fourth machine
   needs a paid tier or a shared node identity.
   **Ruled on 2026-09-28: paid tier; changed on 2026-09-29: stay on Free.**
   W4.2 uses one shared identity, `org-node`. Each joining node gets its own
   Universal Auth client secret under it, and `hq_join leave` revokes that one
   secret (`tools/infisical_setup.py`). `org-node` reads only the `Org-Node`
   project, which holds `CLAUDE_CODE_OAUTH_TOKEN`; the CEO enters the value at
   gate G3 (W4.6c, review task-79219f24).

Also ruled on 2026-09-28: the mesh probes commit to Agents-Core itself (only
`docs/ops/mesh-probe/<from>-<to>.md`, prefix `mesh-probe:`), and a new
machine signs in to claude with a long-lived token from `claude setup-token`
kept in Infisical, so a join has no login step.
