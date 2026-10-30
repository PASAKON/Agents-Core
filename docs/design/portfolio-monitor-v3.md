# Portfolio monitor v3 — the wire contract for the Project page

Status: built in Agents-Core (task-8de1c149, ProjectPage M2); the Console validator and the page are the other half.
Code: `lib/portfolio.py` (`monitor_payload(version=3)`, `_v3_extend`, `link_ph`), `tools/portfolio.py`
(`monitor --v 3 [--counts]`, `ph`), `tools/portfolio_push.py` (`PORTFOLIO_MONITOR_V=3`).
Tests: `tests/test_portfolio_monitor_v3.py` (needs `ORG_TEST_DB_URL`; golden files in `tests/fixtures/`).

v3 is v2 plus, per project row, `ph`, `lead` and `last_event_at`, and one top-level list `unlinked_ph`. It exists so the
Project page can show which session works on a project, whether that session is working, waiting or gone, a link into
its chat in the Claude app, and which live Project Heads (PHs) no row names.

**v1 and v2 are unchanged.** Their bytes for a fixed hub are pinned by `tests/fixtures/portfolio_monitor_v{1,2}_golden.json`,
taken from the library before v3 existed. v1 and v2 carry no `ph`, `lead`, `last_event_at` or `unlinked_ph`.

## 1. Envelope

| | v1 | v2 | v3 |
|---|---|---|---|
| `"v"` | 1 | 2 | 3 |
| max rows in `projects` | 20 (`MAX_ROWS`) | 20 | **40** (`MAX_ROWS_V3`) |
| per-row `ph`, `lead`, `last_event_at` | no | no | yes |
| top-level `unlinked_ph` | no | no | yes, at most **20** (`MAX_UNLINKED_PH`) |

Everything else (`generated_at`, `counts`, `attention`, `orders`, the v2 row fields) is the v2 body, computed the same way.
`counts` and `attention` are taken before the row cap, so they equal v2's. Rows 1 to 20 of v3, minus the three new keys,
are the v2 rows (a test checks it). `monitor_payload(version=...)` accepts 1, 2 or 3 and raises `PortfolioError` for
anything else.

## 2. Shape

```json
{
  "v": 3,
  "generated_at": "2026-10-30T10:00:00Z",
  "...": "counts, attention, orders: as v2",
  "projects": [
    {
      "id": "expert-advisor", "...": "every v2 field",
      "ph":   {"sid": "8dbe4ccc", "host": "contabo", "live": true, "app": "session_01Example", "state": "idle"},
      "lead": {"role": "cto", "sid": "f69c4825", "app": null},
      "last_event_at": "2026-10-30T09:41:07Z"
    }
  ],
  "unlinked_ph": [
    {"sid": "757e61cc", "host": "contabo", "name": "LineOAFile", "lane": "cto", "app": "session_01Example"}
  ]
}
```

(The ids above are made up.)

## 3. Fields

### `projects[].ph` — object or `null`

`null` when the project has no `ph_session`, or the stored value is not a valid sid. Otherwise:

| key | type | meaning |
|---|---|---|
| `sid` | string `^[a-z0-9]{4,16}$` | `projects.ph_session`, bare (a `project_head-` prefix is dropped) |
| `host` | string `^[a-z0-9-]{1,32}$` or null | the host of the PH's live row; the project's own `host` when the PH has no live row; null when neither passes the pattern |
| `live` | bool | a live row exists and its host is not stale (section 4) |
| `app` | string `^session_[A-Za-z0-9]{1,100}$` or null | the Remote Control id of the PH's live row, null when the row has none or the value fails the pattern |
| `state` | one of `running`, `waiting`, `idle`, `parked`, `offline`, `unknown` | section 4 |

`app` is kept even when the host is stale: the page must look at `live` before it offers the link. The page builds
`https://claude.ai/code/<app>` itself and only from an `app` that passes the pattern.

### `projects[].lead` — object or `null`

The C-level that owns the project, from `projects.owner_session` (`cto-f69c4825`, `cmo-ef04792e`, `cto-fresh`):
a role prefix is optional, then 4 to 16 of `[a-z0-9]`. `null` when `owner_session` is empty or does not match
`^(?:[a-z_]{2,20}-)?([a-z0-9]{4,16})$`.

| key | type | meaning |
|---|---|---|
| `role` | string `^[a-z]{2,12}$`, or `"other"` | the project's lane (`cto`, `cmo`, ...) |
| `sid` | string `^[a-z0-9]{4,16}$` | the part after the role prefix |
| `app` | `session_...` pattern or null | the Remote Control id of the live row with that sid, if any |

`lead.app` is null whenever no live row carries that sid. That is the case for `owner_session = cto-fresh`: CTO Main's
live row has its own 8-hex sid, not `fresh`. Four of the 25 monitored projects were in that state on 30 Oct. The fix
belongs in the data (`owner_session` set to the live sid), not in this code.

### `projects[].last_event_at` — string or `null`

The time of the newest row in `project_events` for the project, UTC, `YYYY-MM-DDTHH:MM:SSZ`; null when it has none.
Any event kind counts, including the `ph` verb's. The page's "ตอบแล้ว" is `last_event_at` newer than a press.

### `unlinked_ph[]`

The Project Heads that are live and that no shown row names (section 6). Sorted by `(host, sid)`, at most 20.

| key | type | meaning |
|---|---|---|
| `sid` | `^[a-z0-9]{4,16}$` | the session id |
| `host` | `^[a-z0-9-]{1,32}$` or null | the live row's host |
| `name` | string (at most 80 characters) or null | the project part of the PH's session name `<emoji> PH#<id3> (<LANE>) - <Project>`; null when the name is not of that form; control characters become spaces |
| `lane` | a C-level role from `lib/roles.py` (`cto`, `cmo`, `cgo`, `cfo`, `coo` today) or `other` | the `(<LANE>)` of the name; `other` when absent or unknown |
| `app` | `session_...` pattern or null | as for `ph.app` |

## 4. `ph.state`

Evaluated in this order; the first rule that holds wins.

1. **`parked`** — the project's stage is `parked`. Whatever the PH is doing.
2. **`offline`** — the PH has no row in `live_sessions`, or its host is stale.
3. **`running`** — the live row's `status` is `running`.
4. **`unknown`** — the row's `status` is anything but `idle` (null, or a value this code does not know).
5. **`waiting`** — `status` is `idle` and the PH has something in flight (below).
6. **`idle`** — `status` is `idle` and nothing is in flight.

*Stale.* The rule of `tools/live_sessions.py` itself, read through its own reader (`_snapshot_from_hub`, `DEFAULT_TTL_S` =
150 s, hub clock): a host whose latest `live_hosts.published_at` is older than the TTL, or that never published, marks
every row of that host stale (the reader still returns those rows for a while, flagged stale). On a fresh host a row older
than the TTL is not returned at all, so its PH has no row. Both read as `offline`. When two rows carry one sid, the fresh
host's row wins, then the most recently seen. `tools/live_sessions.py` is not modified.

*In flight.* Either of:

- a row in `tasks` with `owner_cto` equal to the PH's sid and `status` in `pending`, `in_progress`, `review`
  (`IN_FLIGHT_STATUSES`). `state/patrol/ph_patrol.py` groups tasks by the same `owner_cto` but counts only `review`
  and `in_progress`; v3 adds `pending`, a task queued and not yet started, as the brief's "not done" asks;
- a pending Run Inbox card or question whose `requester.session` is the PH's sid (`ask_run.py`'s own client, one
  `GET` of cards and one of questions, `limit=200`, 4 s timeout each).

The Run Inbox is asked at most once per payload, and only when a PH is live, idle and has no task in flight. A Run Inbox
that fails, times out or answers something odd adds nothing: the payload is still built, the PH is `idle`. It logs
nothing, because an error text could carry the hub address.

## 5. Limits and size

| | |
|---|---|
| rows | 40 (v3), 20 (v1, v2) |
| `unlinked_ph` | 20 |
| `unlinked_ph[].name` | 80 characters |
| ids | patterns in section 3 |

The Console reads a push with `express.json({ limit: '64kb' })` (`src/portfolio/routes.js`, `MAX_BODY`). The pusher
sends compact UTF-8 (`separators=(",", ":")`, `ensure_ascii=False`). Measured:

- 40 rows and 20 unlinked, every row with a PH, a lead, a plan and a blocker in Thai (3 bytes a character), 32-character
  app ids: **57 KB** (the test `test_a_full_v3_payload_stays_under_64_kb`).
- All text fields at their caps (120-character Thai names, 100-character app ids): about **76 KB**, over the limit.

A payload over the limit gets HTTP 413, the push is refused, and the page goes stale after 180 s. The real hub is far
below the first number (section 9). If rows ever approach it, raise `MAX_BODY` in the Console first; the Agents-Core
side does not shed rows by itself.

## 6. `unlinked_ph`: what "unlinked" means

A live `project_head` row is listed when its sid is **not named by any row of the payload** (after the 40-row cut). It is
deliberately wider than "has no project row at all": a PH whose project is in stage `idea`, or closed, or beyond row 40,
is outside the monitor, and listing it keeps the page's PH count equal to what `live_sessions` shows. A PH whose
project row is shown never appears here, so the page shows each live PH once.

Not listed: a PH on a stale host, a row whose role is not `project_head`, a sid that fails
`^[a-z0-9]{4,16}$`.

To link one, a lane C-level runs the verb in section 7.

## 7. Command line

```
bash scripts/hub/org-python.sh tools/portfolio.py monitor --v 3            # the JSON
bash scripts/hub/org-python.sh tools/portfolio.py monitor --v 3 --counts   # ph_live=N ph_app=M unlinked=K
bash scripts/hub/org-python.sh tools/portfolio.py ph <project> --session <sid>
```

`--counts` prints one line of three numbers and nothing else: `ph_live` is the live PHs (a project's PH or an unlinked one,
each once), `ph_app` those with an `app`, `unlinked` the length of `unlinked_ph`. No id, no name. It needs `--v 3`.
Nothing in this feature prints a Remote Control id: tests and the CLI show counts only.

`ph <project> --session <sid>` sets `projects.ph_session`. `<sid>` is 4 to 16 of `[a-z0-9]` (a `project_head-` prefix is
accepted and dropped); a bad one is exit 2 and the error does not repeat the value. Who may run it:

- the C-level of the project's lane, the COO, the CEO;
- **never a Project Head**, never a worker, never a C-level of another lane. The refusal is exit 1, is appended to
  `state/reports/portfolio-refusals.jsonl`, and holds **whatever `ORG_PORTFOLIO_ENFORCE` says**: the other verbs let a
  refused caller through while that flag is off, this one has no soft mode.

It refuses a closed or cancelled project and a project that already has that PH (exit 2). It writes one
`project_events` row, actor `<role>-<session>` (`ceo` for the CEO), body `{"op":"ph_link","from":<old or null>,"to":<new>}`,
and prints `{"project","ph_session","from"}`.

The event's `kind` is `heartbeat_rollup` (`PH_LINK_EVENT_KIND` in `lib/portfolio.py`): the CHECK on
`project_events.kind` has no value for a PH link, nothing reads `heartbeat_rollup`, and a new kind is a schema change
(`lib/db_pg.py`, `docs/design/projecttrack-p1-ddl.sql`, a migration on the production hub). When a dedicated kind is
approved, change that one constant and the CHECK together.

## 8. Deploy order

1. Merge Agents-Core v3. The pusher still sends v2: nothing changes on the page.
2. Deploy the Console that accepts and stores v3 (its validator uses the patterns above). Check it with a v3 payload
   from `monitor --v 3` before going on.
3. Only then set `PORTFOLIO_MONITOR_V=3` in the pusher's environment (unset: v2, `1`: v1). The other order sends a body
   the Console refuses with 400, and the page shows "ขาดการเชื่อมต่อ" after 180 s.

To go back, unset the variable: the next push is v2 again.

**The COO gate reads the same payload.** `runners/coo_gate.py` `op_portfolio` calls `portfolio_push.build_payload()` as
the database role `org_coo`, which only has SELECT. v3 also reads `live_sessions.bridge_id`, and
`deploy/coo-gate/org_coo_role.sql` does not grant that column (it lists `host, uuid, sid, role, name, address, status,
pid, seen_at, verified`). So do not put `PORTFOLIO_MONITOR_V=3` in an environment the gate shares with the pusher until
`org_coo` has `GRANT SELECT (bridge_id) ON live_sessions`: until then SomPong's portfolio read fails with
"the portfolio could not be read from the hub". That grant is a change to a production database role, a CEO card, and
is not part of this change. Each process sets the variable on its own, so the pusher can run v3 while the gate stays on v2.

## 9. Known gaps

- **`lead.app` is null for `owner_session = cto-fresh`** (section 3).
- **`waiting` is common.** "Review" counts as in flight, and several live PHs have review tasks that have been open
  since 24 to 29 Oct, so most idle PHs read `waiting` today. The rule is the brief's; the stale tasks are the data to fix.
- **Pending cards may never count.** The pusher's environment may lack the Run Inbox token. Then `_pending_requesters`
  adds nothing, and `waiting` rests on tasks alone. Not tested against a live Console.
- **`_snapshot_from_hub` is private to `tools/live_sessions.py`.** v3 reuses it so that "stale" is one rule; a rename
  there breaks v3 (a test fails).
- **`ph_link` rides on `heartbeat_rollup`** (section 7).
- **`org_coo` cannot read `bridge_id`** (section 8): a v3 read through the COO gate fails until that grant is made.
