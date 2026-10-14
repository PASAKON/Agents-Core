# Org restructure P2 — one C-level per role, Project Heads, spawn gates

Plan: SomPong `docs/reports/org-restructure-ph-envelope-2026-10-13.md` §3, §4.2, §7, §9 (Phase 2).
Built by PH (CTO) #3c1f65ae, landed by CTO #e106b78b. Every piece is behind a flag that
is off on every host until the CEO's OK at deploy (launchers, roles and hooks change how
every session behaves).

## Flags (per host)

A flag is on for a host when the file `/etc/org-flags/<NAME>` exists (root-owned; the deploy
switch), or when the process's own environment says `<NAME>=1` (`lib/org_flags.py`; the launchers
test the same file in bash). The env can turn a flag on, never off. An env-only flag was silently
off on every session started from tmux, the relay or `node_dispatch`, because those take the tmux
server's environment (security review of the launchers piece, 2026-10-13).

| Flag | Off (today) | On |
|---|---|---|
| `ORG_SINGLE_CLEVEL=1` | any number of sessions per C-level role, on any host | the launchers (`cxo-claude.sh`, `cto-claude.sh`) and every spawn path refuse a second live session of a C-level role on this host, and any C-level off Contabo unless `ORG_CLEVEL_EMERGENCY=1` (plan §3.1: Contabo down > 30 min and the CEO typed it) |
| `ORG_PH_ROLES=1` | `project_head` cannot start | `cxo-claude.sh --role project_head --lane <c-level> --project <Name>` and `scripts/spawn-ph.sh` work. What limits a PH does not wait for the flag: the PH tool allowlist, acting only on its own tasks, the 2-worker cap and `merge_task` reading `can_merge` hold for any `project_head` session or PH-owned row, on any host (security review of f73fa02f) |
| `ORG_SPAWN_GATE=1` | only the disk floor (ADR 0030) gates a spawn | `lib/resource_gate.py`: a PH or worker spawn is refused when RAM available < `ORG_SPAWN_RAM_FLOOR_MB` (800) or disk > `ORG_SPAWN_DISK_MAX_PCT` (90 %) |
| `ORG_WORKER_TOKEN_ONLY=1` | a worker with no `RUN_INBOX_TOKEN` falls back to `~/.config/mooniex/run-inbox.token`, the C-level's token, so the hub sees a C-level | `tools/ask_run.py` gives a worker process (`WORKER_TASK_ID` or `WORKER_ROLE` set) no file fallback: it needs its own worker token in `RUN_INBOX_TOKEN`, or it raises no card. Without this flag the Console's worker checks (`freeform_needs_c_level`, `RUN_INBOX_WORKER_SCRIPTS=0`) never meet a Contabo worker (security review of task-fabda3b9) |
| `ORG_SESSION_SCOPE=1` | every claude runs in `org-tmux.scope` with no memory limit | each session's claude runs in its own `systemd-run --scope` with `MemoryHigh` / `MemoryMax` (`ORG_SESSION_MEM_HIGH`, `ORG_SESSION_MEM_MAX`), so the kernel stops only the session that runs away |

Console (MoonieX-Console, its own branch, task-fabda3b9): `RUN_INBOX_WORKER_SCRIPTS=0` (a worker
token may not create script cards, plan T14) and the relay role gate (workers refused, a PH only
for its own project's accounts on its own browser home, `--by` must be the caller's own session;
plan §4.2, T12). The relay gate is on when its marker file exists next to `relay-requests.json`:
the CLI that enforces it runs in the caller's environment, so the env cannot be its switch. No
card caps: the CEO declined them (Q-20261013-2045-0404) and Console #27 was reverted (e3e51fe).

## A Project Head session — the env contract

| Variable | Value |
|---|---|
| `CXO_ROLE` | `project_head` (never a C-level, so every C-level-only tool already refuses it: `ask_ceo`, `ask_run`, `email_ceo`, `start_clevel_remote`) |
| `CXO_SESSION` / `CXO_SESSION_ID` | `1` / the 8-hex id, as for a C-level |
| `ORG_PH_LANE` | the owning C-level role: `cto`, `cmo`, `cgo`, `cfo` or `coo` |
| `ORG_PH_PROJECT` | the project name, `[A-Za-z0-9][A-Za-z0-9_-]{0,39}` |
| `ORG_PH_OWNER` | the session id of the C-level that spawned it (who it reports to) |

- tmux session `project_head-<id>`; lock `state/locks/project_head-<id>.lock`; mailbox box
  `state/inbox/project_head-<id>/`. A worker it delegates is stamped `owner_role=project_head`,
  `owner_cto=<id>`, so the worker's report reaches the PH's box.
- Name: `<MACHINE> Project Head (<LANE>) #<id> (<Project>)`, e.g.
  `CONTABO Project Head (CTO) #3c1f65ae (OrgRestructure)` (the machine prefix is the CEO's
  2026-08-30 rule). `tools/live_sessions.py` reads that shape as role `project_head`.
- Policy row: `policies/agents.yaml` `project_head` — Opus 5.5 (1M) at effort medium (CEO
  2026-10-14, replacing the plan's Sonnet 5.5 at xhigh; C-levels stay Opus at xhigh), `can_merge: false`,
  `can_ask_ceo: false`, `max_workers: 2`. Role doc `roles/project_head.md` is the COO's to write
  (plan §13); the launcher refuses `--role project_head` until it exists.

## Starting a Project Head, and who it talks to

- From inside a C-level session: `bash scripts/spawn-ph.sh --project <Name> --brief-file <path>`
  (`tools/spawn_ph.py`). The caller is whoever `current_identity()` says (a `cto-claude.sh`
  session, which has only `CTO_SESSION_ID`, counts): its role is the lane and its session the
  owner, and `send_to_cxo.authorize(spawning=True)` must allow it. Refused when the flag is off,
  the caller is not such a C-level, the name is bad, the project is held on this host (ignoring
  case: a live PH, or a claim `state/locks/project_head-<id>.project` younger than 60 s whose
  launcher has not written its lock yet), the role doc is missing, or the resource gate says no.
  Check and claim are one step under `state/locks/.ph-projects.flock`. The owner record
  (`project_head-<id>.spawned_by`) is written before the tmux session starts, removed again if it
  fails to start, and removed with the claim when the session ends.
- The launcher starts `--role project_head` only with that owner record: written by root or the
  launching user, naming the `--lane` it was given. Both launchers refuse to start anything from
  inside a Project Head (`CXO_ROLE=project_head`).
- A PH has its own identity (`tools/agent_transport.current_identity`), never the CEO's; with no
  `CXO_SESSION_ID` it cannot send at all. It writes only to its lane: to the session that started
  it while that one is live, else the lane's active session. Live means a launcher pid, not just a
  lock file (`tools/clevel_gate.live_lock`). It never starts a session, it cannot reach another
  lane or another PH, and nothing under it starts one either: its workers' `--spawn` is refused
  whatever the hop count (`tools/send_to_cxo.authorize`). Its wake line always names it
  (`Project Head (<LANE>) #<id>`); `--from` is ignored for a PH, and every wake label is reduced to
  letters, digits, spaces and `_.#()-:/@+` before it is typed into a pane.
- A C-level briefs a PH of its own lane with `send_to_cxo(role="project_head-<id>")`, the name
  `bash scripts/live-sessions.sh` prints; the PH must be live on this host. Another lane's
  C-level is refused (the PH could not answer it); the CEO may brief any PH.
- Not closed in P2: `tools/send_to_worker.py` has no sender check for anyone (unchanged), so a PH
  that runs that CLI by hand can write to any worker. It is not in the PH's MCP tool set.
- One C-level per role (`tools/clevel_gate.py`): the launchers check under a flock and write their
  lock before releasing it. A live session is a lock whose pid is that role's launcher
  (`cxo-claude.sh --role <role>` or `cto-claude.sh` in argv[0] or argv[1]). `send_to_cxo --spawn`,
  relay `spawn_c_level` and `node_dispatch` ask the same gate first only to answer early with the
  reason; a resume there counts the resumed session as live, because it restarts under a new id.

## What is not in P2

- "A PH refuses a 4th job" (plan §3.2, T8 first half) needs the project register: Phase 3.
- Cross-host PH and workers: Phase 4.
- Everything on Contabo runs as root, so a role check is a guard against an honest mistake, not
  against a session that wants around it (it can read any token and set any env). The real
  boundary between sessions stays the permission classifier and the CEO's cards.

## Next security item, after `ORG_WORKER_TOKEN_ONLY`

**A process with no identity in its env is the CEO.** `tools/agent_transport.current_identity` maps a
process with `CXO_ROLE`, `WORKER_TASK_ID` and `CTO_SESSION_ID` all unset to `CEO_IDENTITY`. So any session
with a shell can run `env -u CXO_ROLE -u CXO_SESSION_ID python -m tools.send_to_cxo --from CEO …`. The
letter goes in as `ceo:ceo` to any lane, `authorize()` passes it as a root peer, `--spawn` is allowed,
and the reader sees "from CEO". With envelope mail on, the kind/prio tag rides along too. This predates
P2 (security review of the send_to_cxo kind/prio branch, 2026-10-14) and is logged for the CEO by CTO
#e106b78b. Direction: an env with no identity is refused, and the CEO identity needs something a session
cannot set: the relay's pinned sender, or a root-only marker the CEO's own terminal carries. Two LOW items
from the same review go with it:
- `lib/mailbox.py` still writes `kind: order` for any caller in the same process. The COO user has an
  ACL on every box, so `hook-inbox` should show "order" only for a letter it can verify.
- The subject guard catches only a subject starting `order #`.
