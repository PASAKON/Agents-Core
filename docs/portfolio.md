# Portfolio Collector & Monitor Schema (`lib/portfolio.py`)

`lib/portfolio.py` collects project, order, Project Head (PH), worker, and host telemetry from the hub (`projects`, `milestones`, `orders`, `tasks`, `live_sessions`, `live_hosts`) and publishes the snapshot via `tools/portfolio_push.py`.

## Per-PH Worker-Host Suffix & Counts (`hosts[].sessions`)

Under Order O-20261103-2233-6e3a, each Project Head's session name carries a trailing suffix showing which machines its `in_progress` workers are running on (`lib/session_names.py:ph_worker_suffix`), while the leading emoji remains the PH's own host (`🌐` `contabo`, `🖥️` `winbox`, `💻` `mac`):

- **No running worker**: `""` (no suffix)
- **Workers on one host**: `" · <emoji> <host>"` (e.g. `" · 🖥️ winbox"`)
- **Workers on several hosts**: `" · <emoji><count> <emoji><count>"` in fixed host order `contabo`, `winbox`, `mac` (e.g. `" · 🖥️1 💻1"`)

The portfolio collector exposes the same suffix and per-host worker counts in `hosts[].sessions` (collected by `lib.portfolio.collect_host_sessions` / `lib.portfolio.host_sessions` and `lib.portfolio.ph_worker_hosts`):

```json
{
  "name": "contabo",
  "online": true,
  "fill_pct": 42,
  "fill_basis": "ram",
  "ram_free_gb": 14.2,
  "disk_free_gb": 180.5,
  "waiting_host": 0,
  "sessions": [
    {
      "sid": "053a1b2c",
      "role": "project_head",
      "name": "🌐 PH#053 (CTO) - CookieRun · 🖥️ winbox",
      "status": "idle",
      "worker_hosts": {
        "winbox": 1
      },
      "worker_suffix": " · 🖥️ winbox"
    }
  ]
}
```

### `hosts[].sessions[]` Fields

| Field | Type | Description |
|---|---|---|
| `sid` | `string` | Bare 8-hex session ID (or 3-hex short ID for unverified remote rows). |
| `role` | `string` | Session role (`"project_head"`, `"cto"`, `"cmo"`, `"coo"`, `"cfo"`, `"cgo"`, etc.). |
| `name` | `string` | Sanitized display name (max 120 chars, Remote Control app IDs stripped). |
| `status` | `string` | Live session status (`"running"`, `"idle"`). |
| `worker_hosts` | `object` | *(PH sessions only)* Map of `{host: count}` for `in_progress` worker tasks owned by this PH (`tasks.owner_cto`), ordered by `("contabo", "winbox", "mac")`. Empty `{}` when no worker is running. |
| `worker_suffix` | `string` | *(PH sessions only)* Rendered suffix from `lib.session_names.ph_worker_suffix(worker_hosts)` (`""`, `" · 🖥️ winbox"`, or `" · 🖥️1 💻1"`). |

### Wire Compatibility with Monitor v3 / v4

- `lib.portfolio.monitor_payload(version=4)` preserves `hosts[].sessions` as the integer count of non-stale sessions on each host so the existing Console v4 wire validator remains unchanged, while `projects[].workers` carries the per-project worker list (`title`, `state`, `host`).
- `lib.portfolio.collect_host_sessions(conn=...)` (or `_v4_hosts(conn, detailed_sessions=True)`) returns `hosts[].sessions` as the detailed session list with `worker_hosts` and `worker_suffix` on each PH session for the Console `/project` card.
- `lib.portfolio._ph_name_lane(name)` strips the trailing ` · <workers>` suffix via `lib.session_names.PH_NAME_RE` so `unlinked_ph[].name` always reports the clean project name.
