# tasks.db → one registry on Contabo (the hub), Mac/winbox as spokes

- **Date:** 2026-09-18 · **Owner:** CTO (session e8565613, carried from 4a904905)
- **Ruling:** CEO 2026-09-17 ruling 5 (memory `project_org_session_architecture_2026_09`):
  *Contabo = hub of the Agents repo (always online); Mac and winbox are spokes;
  tasks.db moves there.* This document is the HOW; the WHAT is not re-argued.
- **Supersedes:** ADR 0024 §Recommendation (Mac hub + Contabo front door) and
  ADR 2026-07-12 Phase D (skip cutover, two independent databases).
- **Keeps:** `docs/design/multi-host-workers.md` rules 2–3 (git is the truck;
  the hub pushes to spokes, Contabo→Mac stays closed).

## 1. Measured state (2026-09-18 02:30, all read-only)

| | Mac `state/tasks.db` | Contabo `/opt/mooniex-agents/state/tasks.db` | winbox |
|---|---|---|---|
| size / rows | 19.9 MB · 910 tasks · 137 c_level_sessions · 57 open | 118 KB · 11 tasks (all terminal, Sep 11–12, owner e1e3d3ef) · 3 sessions | no tasks.db (git clone only, 59 worktrees) |
| id overlap | — | 0 of 11 exist on Mac | — |
| writers | CTO/CXO MCP servers, worker MCP, watchdog (launchd), hooks, ~18 tools | 2 live CTO sessions (6ebacd0e, e1e3d3ef — CEO active 01:54) | none |

- `lib/db.py` (772 lines) is the access layer for **33** non-test modules; **11** more open
  `sqlite3` themselves (`lib/ceo_report.py`, `lib/session_search.py`, `scripts/hook-self-repo-guard.py`,
  `scripts/hook-log-prompt.py`, `scripts/hook-log-dev-reply.py`, `scripts/session_orphan_report.py`,
  `scripts/session_tree.py`, `scripts/browser/tab_registry.py`, `tools/claudesign_tmux_bin.py`;
  `runners/relay_mcp_server.py` + `runners/secretary_server.py` own *other* databases and stay as they are).
- SQLite-only SQL is small: 32 `?` placeholders, 1 `INSERT OR REPLACE`, 1 `AUTOINCREMENT`,
  4 `PRAGMA`, 1 `executescript`, `sqlite3.Row` in 4 files, `LIKE` in 8 (case-sensitivity differs).
- Network: Mac→Contabo tailnet RTT **127 ms avg (50–198)**; Mac→winbox 59 ms. Contabo
  `ts-input` accepts everything on `tailscale0`, so a service bound to `100.118.171.23`
  is reachable from the tailnet and from nowhere else (ufw allows only 22/80/443 publicly).
- Contabo: docker present (no postgres image yet), 4.3 GB RAM free, 28 GB disk free,
  tree 41 behind / 8 ahead of origin (the 8 are already merged into Mac main via eb49fae8).

## 2. Decision

**Postgres 16 on Contabo, bound to the tailnet IP only; `lib/db.py` grows a second
backend selected by `ORG_DB_URL`; SQLite stays the default (tests, offline fallback).**

Why not the alternatives:
- *SQLite file on Contabo shared over a mount* — unsafe (locking), rejected by ADR 0024 too.
- *rqlite* (SQLite over HTTP) — keeps the dialect but has no client-side transactions: the 15
  `with get_conn():` blocks in `lib/db.py` would silently lose atomicity across ≥3 writers.
- *Supabase Postgres* — reachable everywhere, but org state would sit in the customer DB
  account that is itself mid-migration to a new owner; self-hosted on the hub is one hop shorter.
- *Run the Mac's org MCP server on Contabo over ssh* — moves DB writes but also moves
  `delegate_task`/`merge_task`, which need the Mac's checkouts and Chrome. Not viable.

Cost accepted: every statement from the Mac pays ~127 ms. Hot paths are short (an MCP tool
call is ≤ ~20 statements ≈ 2–3 s worst case); the watchdog runs in the background; the two
per-tool-call hooks get a 3 s timeout and **fail open** with a log line.

## 3. What changes

### 3.1 `lib/db.py` — dual backend (task W1)
- `ORG_DB_URL` unset → SQLite exactly as today. Set (`postgresql://…`) → psycopg 3.
- One connection wrapper so callers keep writing SQLite-style SQL: `?` → `%s`; row objects
  support both `row["col"]` and `row[0]` (sqlite3.Row parity); `PRAGMA` no-op; `executescript`
  split on `;`; `INSERT OR REPLACE` → `ON CONFLICT (pk) DO UPDATE`; DDL has a Postgres
  variant (`AUTOINCREMENT` → `GENERATED ALWAYS AS IDENTITY`). `LIKE` audited per call site.
- `get_conn()` keeps its commit/rollback contract — that is the reason for Postgres.
- The 9 bypassers above go through `lib.db.get_conn()` (read-only ones may keep a SQLite
  fallback when `ORG_DB_URL` is unset). Hooks: timeout + fail-open.
- `scripts/migrate_tasks_db.py`: SQLite → Postgres, idempotent by primary key, prints per-table
  counts on both sides; refuses to run if counts already differ in the wrong direction.
- Tests: existing suite unchanged on SQLite; a second run of the DB-touching tests against a
  local `postgresql@16` (brew) selected by `ORG_TEST_DB_URL`. ADR 0021 stands: no test touches
  real state.

### 3.2 Contabo (hub) — needs explicit CEO OK before the first command
- `docker run postgres:16` with a named volume, `-p 100.118.171.23:5432:5432`, password in
  `/root/.config/mooniex/org-db.env` (chmod 600), DB `org`, plus `org_test` for spoke test runs.
- Nightly `pg_dump` to `/opt/mooniex-agents/state/backups/` (the existing Drive broker can
  ship it later; not in this session's DoD).
- No change to `/opt/mooniex-agents` tree while sessions 6ebacd0e / e1e3d3ef are live.

### 3.3 Cutover runbook (Mac first, Contabo sessions last)

Steps 1-5 are automated by `scripts/hub/cutover-mac.sh` (task-78586938) --
dry-run by default (prints what every step would do, touches nothing),
`--apply` to execute for real. Reads `ORG_DB_URL` from
`~/.config/mooniex/org-db.env` at run time (refuses if that file is
missing); routes it into `config/cto.mcp.json`, `config/worker.mcp.json`,
the watchdog + mac-agent launchd plists, and `scripts/cto-claude.sh` via
`scripts/hub/with-org-db-env.sh` (`scripts/hub/cutover_flip.py` does the
file edits and prints a diff) -- a wrapper indirection, not the literal
value, so the secret never lands in the two git-tracked JSON files. Steps
6-7 below (Contabo's own delta) are not yet automated.

1. Freeze Mac writers: `launchctl bootout` the watchdog; no `delegate_task` during the window
   (worker tasks in flight keep running — they write through their MCP server, so pick a
   moment with none pending; 2 are live now).
2. `migrate_tasks_db.py --from state/tasks.db --to $ORG_DB_URL` → counts match (910/137/…).
3. Flip the Mac: `ORG_DB_URL` in `config/cto.mcp.json` + `config/worker.mcp.json` env,
   the watchdog + mac-agent launchd plists, `scripts/cto-claude.sh` export. Restart watchdog.
4. Verify: `create_task` from a Mac session → row visible from Contabo (`psql`), `get_task`
   round-trips, watchdog tick logs against the hub.
5. `mv state/tasks.db state/tasks.db.archived-2026-09-18` — file must never gain an mtime again.
6. When the CEO ends/restarts the two Contabo sessions: pull the tree to origin/main, import
   Contabo's rows (`--from /opt/mooniex-agents/state/tasks.db`, 11 tasks + 3 sessions + any
   delta since 02:30), set `ORG_DB_URL` in `scripts/cto-claude.sh`'s Contabo branch, archive
   its sqlite the same way.
7. Live sessions already open on the Mac keep their old MCP servers until restarted — they
   would write to the archived file. So step 5 happens only after every Mac C-level session
   has been restarted (`/terminal-restart`), or their rows are re-imported as a delta.

### 3.4 Watchdog scoping (follow-up W2, not this session's DoD)
One registry means the Mac watchdog now sees Contabo-owned rows. Today it already branches on
`host` (`_sweep_remote_terminal_task`, `_check_remote_stall`) and can reach both spokes over
ssh, so nothing double-reaps. A Contabo watchdog (systemd) for the hours the Mac sleeps is
W2, together with GH #155's PATH/env fix.

## 4. Definition of Done (this session)
- [ ] W1 merged on main; suite green on SQLite and on Postgres; `ORG_DB_URL` unset = old behaviour.
- [ ] Contabo Postgres holds Mac 910 tasks / 137 sessions (+ Contabo's 11 / 3 once its sessions restart); counts printed from both sides.
- [ ] Mac runtime flipped: a `create_task` from this session is visible from Contabo; `state/tasks.db` archived with no writer.
- [ ] ADR 0025 written (supersedes ADR 0024 recommendation + ADR 2026-07-12 Phase D); org wiki `projects/mooniex-agents.md` changelog.

## 5. Risks
- **Mac offline = Mac sessions cannot write.** Accepted by the ruling (Contabo is the always-on
  box; the Mac was the single point of failure before). SQLite fallback is for tests only —
  a silent local fallback would recreate the split brain this fixes.
- **Latency** — measured, see §2. If a tool call is ever felt as slow, the fix is fewer
  statements, not a local cache.
- **Two live Contabo sessions** keep writing to their own sqlite until restarted; their delta is
  imported in step 6. Nothing is deleted before it is read (ADR 0024 last section).
