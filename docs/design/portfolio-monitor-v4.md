# Portfolio monitor v4

`lib.portfolio.monitor_payload(version=4)` extends v3. Versions 1, 2 and 3 retain
their existing payloads. The envelope has `v: 4`; all v3 fields and limits remain.
Times are UTC, formatted `YYYY-MM-DDTHH:MM:SSZ`, or null. New text fields have
control characters removed and are truncated without an ellipsis. Remote app
identifiers belong only in the inherited `app` fields.

## Project additions

| Key | Meaning |
| --- | --- |
| `opened_at` | Project opening time, or null; also the size-shedding sort key. |
| `stage` | `active`, `parked`, `ready`, `closed`, or `other`. |
| `workers` | Up to eight tasks owned by the PH's bare sid or `project_head-<sid>`, updated within seven days, newest creation first. |
| `review_n` | All review tasks owned by that PH, including older tasks and tasks beyond the eight-item cap. |

Each worker has exactly `title` (at most 60 characters), `state`, and `host`.
Host values must match `^[a-z0-9-]{1,32}$`, otherwise null. Task states map as follows:

| Task status | Wire state |
| --- | --- |
| `in_progress` | `running` |
| `pending` | `queued` |
| `blocked_host` | `waiting_host` |
| `blocked` | `blocked` |
| `stalled` | `stalled` |
| `review` | `review` |

## Order additions

`by` is the role prefix of `taken_by`, matching `^[a-z]{2,12}$`, or `other`
for an invalid role, or null when not taken. For example, `cto-fresh` yields `cto`.
`project_closed` is true exactly when the linked project's stage is `closed`
and its closing time is at or after the order's taking time. Consumers count
these orders as done and omit them from the visible job list.

## New lists

`clevel_work` contains at most 20 tasks owned by `cto-*`, `cmo-*`, `coo-*`,
`cfo-*`, or `cgo-*`, excluding owners named as PH by any project, including
projects outside the displayed rows. Tasks must have one of the worker statuses
above except `review`, and an update within seven days. Newest creation comes
first. Each entry has exactly `lane` (role or `other`), `title` (60 characters),
`state`, `host`, and `created_at`. The page's combined C-level job cards put CEO
blockers first, running jobs next, and the remainder newest first; this list
supplies the task portion of those cards.

`hosts` contains at most five valid hosts, sorted by name. Resource readings
come from the read-only `tools.host_fill.collect()` library call. If that call
fails, the list is empty. Each entry has exactly:

| Key | Type / source |
| --- | --- |
| `name` | Host pattern above. |
| `online` | Boolean from the collector. |
| `fill_pct` | Integer 0–999, rounded half up and clamped, or null. |
| `fill_basis` | `ram`, `cpu`, `disk`, `load`, or null. Load means one-minute load per core ×100. |
| `ram_free_gb` | Finite nonnegative number or null. |
| `disk_free_gb` | Finite nonnegative number or null. |
| `waiting_host` | Count of all `blocked_host` tasks assigned to that host. |
| `sessions` | Count of fresh live-session rows on that host, using the existing live-session reader. |

The current collector reports `highest` as its basis and does not expose disk
free space. Its Unix CPU reading is load per core, so v4 labels that reading
`load` using the host registry's operating system. Unavailable disk data is
null; v4 performs no extra host probes.

`parked_ph` contains at most 20 entries sorted by `(host, sid)`. It reads only
this host's `state/locks/project_head-<sid>.project.parked` files. A sid with a
row in the existing live snapshot is excluded. Each entry has exactly `sid`
(the v3 sid pattern), `project` (file content matching
`^[a-z0-9][a-z0-9-]{0,63}$`, otherwise null), and `host` (host pattern or null).
Unreadable files and invalid sids are skipped.

## Size and rollout

`MAX_BODY` is 128 × 1024 bytes of compact UTF-8 JSON. If oversized, clear
workers lists one project at a time, oldest `opened_at` first (null first,
project id breaks ties). Stop as soon as the payload fits. If still oversized,
clear `clevel_work`. If it still cannot fit, raise `PortfolioError` and send
nothing. Empty lists remain present so the exact key contract is preserved.

Deploy Console acceptance of v4 while retaining v1–v3 first. Then set
`PORTFOLIO_MONITOR_V=4` for the pusher and restart its loop. Unset remains v2;
explicit 1, 2, and 3 retain their behavior. This change does not deploy or
restart any service. The command-line monitor's version choices are unchanged.
