# Org restructure P3 — project registry, GO register, resource locks, Project Monitor backend

Written by PH OrgRestructure #7cf528f0, 14 Oct 2026. **GO from CTO Main 03:04Z** (cto-c34459eb), in the order
below (P3-A and 09d85a20 first, ≤2 workers). Every Agents-Core and Console piece lands as a PR that CTO Main
merges; nothing is pushed to main. Workers remove their worktree once landed (Contabo disk).

Sources: SomPong `docs/reports/org-restructure-ph-envelope-2026-10-13.md` §4.3, §5, §7, §9 Phase 3, and
`docs/reports/project-monitor-widget-2026-10-14.md` (v2). CEO GOs: P3 itself sits in the restructure plan the
CEO ordered on 13 Oct. Project Monitor is Q-20261014-0047-6955, choice 0, "ตามนี้ ทำพร้อม Phase 3"
(answered 00:49:19Z, verified on the hub by CTO Main).

Out of scope here: the Scriptable widget itself (Mac Scriptable lane, deployed from the Mac), cross-host PH
and workers (Phase 4), and the Console web page `/portfolio` (listed as P3-F below, in the Console repo).

## What P3 ends (the "practice until Phase 3" lines in roles/project_head.md)
| Practised by hand today | P3 replaces it with |
|---|---|
| The C-level puts the ready-gate items in the brief; `spawn-ph` checks only host, role file, lane and name | `spawn-ph` refuses unless the project's registry row passes the ready gate |
| A PH keeps milestones, blocker and "decided for CEO" in `STATUS.md` and repeats them in each report | `portfolio_update` writes them to the hub; `STATUS.md` keeps the story only |
| "using <resource> until <time>" in a report; ask the C-level who holds a browser home or render slot | `resource_lock` rows with a holder, project and expiry |
| The brief quotes the CEO's GO and its number | `ceo_gos` rows with scope, cap and expiry; a spend cites the row id |
| % by hand | % = milestones with evidence ÷ total, computed |

## Pieces (each one is a worker-sized job with its own branch, tests and review)

### P3-A Hub tables (Agents-Core `lib/db_pg.py`, ADR 0008 rules: plain `CREATE TABLE IF NOT EXISTS`, indexes for each read path, no secret columns)
- `projects`: `id` (slug, PK), `name`, `lane` (cto/cmo/…), `owner_session`, `ph_session`, `host`, `repos`
  (json list, P3-H), `stage`
  (`idea|brainstorm|ready|active|review|closed|parked|cancelled`), `goal`, `done_criteria`, `budget_usd`,
  `relay_accounts` (json list), `blocker_what`, `blocker_on` (`ceo|clevel|external|resource`),
  `blocker_since`, `opened_at`, `ready_at`, `closed_at`, `outcome`, `hq_row`, `last_active`.
- `project_events`: append-only (`id`, `project_id`, `at`, `kind`, `actor`, `body` json). Kinds: opened, stage,
  milestone, blocker, unblocked, decided_for_ceo, ceo_go, spend, closed, heartbeat_rollup. Enforced with a
  `BEFORE UPDATE OR DELETE` trigger that raises. (Memory note: a BEFORE DELETE trigger must raise, not
  `RETURN NEW`; NEW is NULL on DELETE.) A second, statement-level trigger refuses `TRUNCATE`. Both stop
  accidents only: the hub role `org` is a superuser and owns the table, so it can disable or drop them.
  True append-only needs the INSERT-only writer role from the grants piece.
- `milestones`: `project_id`, `n`, `title`, `done_at`, `evidence` (required when `done_at` is set: sha,
  Drive id, URL or path; a CHECK constraint).
- `ceo_gos`: `id`, `words` (verbatim), `source` (`run:Q-…`, `run:RUN-…` or `chat:<session>`),
  `project_id`, `action`, `max_usd`, `given_at`, `expires_at`, `used_by`, `used_at`. The CHECK on `source`
  validates the format only; the tools piece must look each `Q-`/`RUN-` id up in the Run Inbox before writing.
- `resource_locks`: `resource` (PK, e.g. `browser_home:contabo:3`, `render_slot:h3`), `holder_session`,
  `project_id`, `since`, `until`. A stale lock (past `until`) is free.
- `post_ledger`: `platform`, `account`, `url`, `posted_at`, `views_48h`, `read_at`, `project_id`.
- `session_heartbeats`: `session_id` (PK), `project_id`, `at`. Upsert, one row per session (not a log).
- Money spent is read from `docs/ops/credit-ledger.jsonl` (`tools/credit_ledger.py`); the PH never reports
  it by hand. A later step can move that ledger into the hub; P3 only reads it.
- Tests: schema in a throwaway Postgres (the existing hub test harness), the append-only trigger, and the
  evidence CHECK.

### P3-B `tools/portfolio.py` (CLI + MCP `portfolio_update` / `portfolio_show`)
- Verbs: `open`, `stage`, `milestone add|done --evidence`, `block --on --what`, `unblock`, `decided`,
  `go add|use`, `park`, `close --outcome --learning`, `lock take|release`.
- Who may write is decided by the caller's identity (`agent_transport.current_identity`, so the P3 work
  should land after the 09d85a20 strict-identity flag): a PH only its own project, a C-level only its lane's
  projects, the COO all of them for seeding. Workers are read-only.
- `portfolio_report --week|--month`: no model. It reports opened, closed, active and stuck projects (on what,
  waiting on whom), mean days, spend vs budget and decisions made for the CEO. It is appended to the Monday
  `tools/tool_value.py` report.
- `spawn_ph.py` gains the ready-gate check: a `ready` row with a goal, done criteria, owner, host, budget,
  ≥3 milestones and, when it spends money or is new, a `ceo_gos` row. Behind a new flag `ORG_PH_REGISTRY`,
  log-only first, like P2.

### P3-C Heartbeat hook (Project Monitor signal 1)
- A new PostToolUse hook (`scripts/hook-heartbeat.py`, system python3 in the hook path): a session with
  `CXO_SESSION_ID` or `WORKER_TASK_ID` writes `(session_id, ts)` at most once a minute.
- Hooks cannot reach the hub (no `ORG_DB_URL` and no psycopg under the system python3, a memory note), so
  the hook appends to `state/reports/heartbeat.jsonl`, and the live-sessions publisher loop (it already runs
  per host with the hub env) folds it into `session_heartbeats` and `projects.last_active` once a minute.
  It costs zero tokens and adds one file append per tool call at most once a minute.
- Session → project: from `state/locks/project_head-<id>.project` (spawn_ph writes it) and, for a worker,
  the task row's `project` / its PH owner.

### P3-D `project_id` on cards and relay (Project Monitor signal "Waiting CEO")
- Agents-Core: `tools/ask_run.py` (`ask`, `run`) and the relay request CLI take `--project <id>`, defaulting
  to the caller's PH project. The org MCP tools pass it through.
- Console (its own repo and lane, a separate branch): one nullable `project_id` column on `run_asks`,
  `run_questions` and relay requests, accepted by the create endpoints and shown on the card. No behaviour
  change when it is absent. Per the HQ rule the two projects meet only at the API.

### P3-E Read-only JSON endpoint for the widget
- Lives in Console (it already serves terminal.mooniex.com): `GET /api/portfolio/monitor.json`. It reads
  the hub through a read-only Postgres role (like `org_coo`: SELECT on the P3 tables only) plus its own
  card tables for "Waiting CEO".
- The response is one row per project in `active|review|parked`, with evidence of real work (≥1 commit,
  task, job or run): `name`, `pct`, `state`, `state_since`, `active_today_s`, `parked`. States follow the
  v2 design rules in order, first match wins: Working, Generating, Waiting CEO, Waiting, Idle, Stalled,
  Parked. Sort: in progress by newest `last_active`, then parked.
- Auth: the token the widget already uses for the RAM widget endpoint, or a new read-only token in
  Infisical (Console project). It never returns secrets, chat text or card command bytes.
- "Generating" in v1 reads only signals that exist today: an H3 job API call and a running worker task of
  that project. Flow, Higgsfield and pipeline runs come later, one per adapter.

#### P3-E contract (fixed before either side builds; a change is a versioned `v`)
`GET https://terminal.mooniex.com/api/portfolio/monitor.json`, header `Authorization: Bearer <read-only token>`.
`200`, `Content-Type: application/json`, `Cache-Control: no-store`:
```json
{
  "v": 1,
  "generated_at": "2026-10-14T03:20:00Z",
  "counts": {"in_progress": 7, "parked": 2},
  "projects": [
    {
      "id": "black-liquidity",
      "name": "BLACK LIQUIDITY",
      "lane": "cmo",
      "pct": 75,
      "milestones": {"done": 6, "total": 8},
      "state": "generating",
      "state_since": "2026-10-14T03:02:00Z",
      "last_active": "2026-10-14T03:19:40Z",
      "active_today_s": 6000,
      "blocker": null,
      "parked": false
    }
  ]
}
```
- `state` is one of `working | generating | waiting_ceo | waiting | idle | stalled | parked` (v2 design rules,
  first match wins). `pct` is an integer 0–100 = `round(100 * done / total)`, and `0` when `total` is 0.
- `blocker` is `null` or `{"on": "ceo|clevel|external|resource", "since": "<ISO>"}`. It never carries the
  blocker's text (the widget has no room, and the text can name accounts).
- Times are UTC ISO-8601 with `Z`; `active_today_s` counts from 00:00 Asia/Bangkok.
- Order: every non-parked row by `last_active` desc, then parked rows by `last_active` desc. The server
  sends at most 20 rows; the widget cuts from the bottom.
- `401` without a valid token, `503` `{"v":1,"error":"hub unreachable"}` when the hub is down. Never a
  stack trace, a card's command bytes, chat text or an account name.
- Tests on both sides read one fixture file, `docs/plans/fixtures/portfolio-monitor-v1.json` (Agents-Core),
  copied into Console's tests, so the shape cannot drift silently.

### P3-F Console `/portfolio` page (phone, read-only)
- By lane: active projects with % and blocker, the number waiting on the CEO, the idea box, and projects
  closed this week or month. Console repo, after P3-E (same query).

### P3-G Seed
- The 14 projects the CEO accepted for the monitor (Film 2 parked, the websites excluded), plus the live PH
  projects (SpendGuard, CooGate, OrgRestructure, MimiPage, BlackLiquidity). The COO seeds from `hq.yaml`,
  `config/projects.yaml`, LungNote `[SID:]` todos and live sessions, and flags incomplete rows for the
  owning C-level. The `STATUS.md` milestone tables that PHs keep today are imported once.

### P3-H `can_merge` scoped per project (CEO ruling ~10:00 TH 14 Oct, now in roles/project_head.md)
- `projects.repos` (json list of `PASAKON/<repo>`) holds the PH's own repos, set by its C-level at
  `open`/`ready`.
- `merge_task` (and any PH merge path) lets a `project_head` caller merge only when all of these hold:
  - the task's repo is in its project's `repos`;
  - `CTO_Gate_MergeChecklist` passes;
  - the tests the task names pass;
  - a second reviewer's session id is recorded on the task (`review_by`, not the PH itself and not the
    worker that wrote it).
- Refused for a PH whatever `repos` says: Agents-Core, Agents-Rules, Console, and any path under hooks,
  launchers (`scripts/*-claude.sh`, `spawn-*.sh`) or MCP servers. Those land through the lane's C-level.
- Behind `ORG_PH_REGISTRY` with the rest, log-only first: the check runs and logs its verdict, and
  `can_merge` stays as today until CTO Main switches it on. Depends on P3-A (the `repos` column) and
  09d85a20 (the caller's identity cannot fall back to the CEO).
- Tests: each refusal reason, the second-reviewer rule, a shared-system repo listed in `repos` still
  refused, and the C-level path unchanged.

## Order and size (estimates, not measured)
| Step | Depends on | Repo | Size | Runner (CXO_Gate_RouteFirst) |
|---|---|---|---|---|
| P3-A tables | — | Agents-Core | M | Argon (file-scoped, PH runs the tests); trigger and grants reviewed by the PH |
| 09d85a20 strict identity (log-only) | — | Agents-Core | S | Opus worker (`override: security`) |
| P3-B portfolio.py + ready gate (log-only) | A, 09d85a20 | Agents-Core | M | Argon or Codex; PH review |
| P3-C heartbeat hook + fold | A | Agents-Core | S | Argon; PH review (hook path) |
| P3-D project_id, Agents-Core side | — | Agents-Core | S | Argon |
| P3-D/E/F Console side | A, D | Console | M | Console lane, own branch; PH review on the API contract |
| P3-G seed | B | — | S | COO, through `portfolio` |
| P3-H per-project `can_merge` (log-only) | A, 09d85a20 | Agents-Core | M | Opus worker (`override: security`); PH review |
| Widget | E | Scriptable (Mac) | — | Mac Scriptable lane |
Total about 4–6 working days for workers plus review. The PH stays at ≤2 workers at a time.

## Switch-on and rollback
- New flag `ORG_PH_REGISTRY` (file in `/etc/org-flags/`, same rule as P2): off means `spawn-ph` works as
  today. On means it refuses a project without a ready registry row. Log-only for 3 days, then CTO Main
  decides.
- The tables, hook, CLI and endpoint are additive. Rollback is the flag file plus removing the hook entry.
  The tables stay (no data loss).
- Root steps on Contabo (flag file, a Postgres role) go on Run cards that CTO Main raises.

## Answers (CTO Main 03:04Z)
1. The endpoint lives in Console. The contract above comes first, before either side builds.
2. `credit-ledger.jsonl` stays a file in P3.
3. An idea row is one line. This is not a CEO question.
