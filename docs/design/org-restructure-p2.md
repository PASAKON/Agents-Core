# Org restructure P2 — one C-level per role, Project Heads, spawn gates

Plan: SomPong `docs/reports/org-restructure-ph-envelope-2026-10-13.md` §3, §4.2, §7, §9 (Phase 2).
Built by PH (CTO) #3c1f65ae, landed by CTO #e106b78b. Every piece is behind a flag that
is off on every host until the CEO's OK at deploy (launchers, roles and hooks change how
every session behaves).

## Flags (per host, in the launching environment)

| Flag | Off (today) | On |
|---|---|---|
| `ORG_SINGLE_CLEVEL=1` | any number of sessions per C-level role, on any host | the launchers (`cxo-claude.sh`, `cto-claude.sh`) and every spawn path refuse a second live session of a C-level role on this host, and any C-level off Contabo unless `ORG_CLEVEL_EMERGENCY=1` (plan §3.1: Contabo down > 30 min and the CEO typed it) |
| `ORG_PH_ROLES=1` | `project_head` cannot start | `cxo-claude.sh --role project_head --lane <c-level> --project <Name>` and `scripts/spawn-ph.sh` work; the org MCP serves a PH the reduced tool set; `merge_task` reads `can_merge`; a PH may run at most `max_workers` (2) live workers |
| `ORG_SPAWN_GATE=1` | only the disk floor (ADR 0030) gates a spawn | `lib/resource_gate.py`: a PH or worker spawn is refused when RAM available < `ORG_SPAWN_RAM_FLOOR_MB` (800) or disk > `ORG_SPAWN_DISK_MAX_PCT` (90 %) |
| `ORG_SESSION_SCOPE=1` | every claude runs in `org-tmux.scope` with no memory limit | each session's claude runs in its own `systemd-run --scope` with `MemoryHigh` / `MemoryMax` (`ORG_SESSION_MEM_HIGH`, `ORG_SESSION_MEM_MAX`), so the kernel stops only the session that runs away |

Console flags (MoonieX-Console, its own branch): `RUN_INBOX_WORKER_SCRIPTS=0` (a worker token
may not create script cards, plan T14), `RUN_INBOX_CARD_CAPS=1` (per-session caps on command and
script cards, Console #27), `RELAY_ROLE_GATE=1` (relay requests: workers refused, a PH only for its
project's accounts, `--by` must be the caller's own session; plan §4.2, T12).

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
- Policy row: `policies/agents.yaml` `project_head` — Sonnet 5.5 (1M) at xhigh, `can_merge: false`,
  `can_ask_ceo: false`, `max_workers: 2`. Role doc `roles/project_head.md` is the COO's to write
  (plan §13); the launcher refuses `--role project_head` until it exists.

## What is not in P2

- "A PH refuses a 4th job" (plan §3.2, T8 first half) needs the project register: Phase 3.
- Cross-host PH and workers: Phase 4.
- Everything on Contabo runs as root, so a role check is a guard against an honest mistake, not
  against a session that wants around it (it can read any token and set any env). The real
  boundary between sessions stays the permission classifier and the CEO's cards.
