# Questline

Work-as-a-game. City-builder + factory-belt visual (Cities:Skylines / OpenTTD zone-growth,
Factorio/Satisfactory belt-flow) over real work data — org tasks + personal todos.

## Run

```
python3 export_state.py                # regenerate state.json from tasks.db + snapshot
python3 -m http.server 8642            # index.html fetches state.json — file:// is CORS-blocked
open http://localhost:8642
```

## How it maps to real data

- **DEV district** — org tasks (`state/tasks.db`) with role in developer/web_designer/backend_dev/
  frontend_dev/devops_engineer/tester/qa/security_engineer
- **GROWTH district** — same db, role in content_strategist/ads_manager/prompt_engineer/data_analyst
- **LIFE district** — personal todos, from `data/personal_todos_snapshot.json`
- **HQ tower** — meant to level up from real org KPIs (signups/revenue/tasks-merged). Stubbed at
  level 1 for now — not wired yet.

Each district: `tier` (1-5, from completed count), `backlog` (crates, capped at 20 drawn),
`belt_speed` (completions in last 7 days / 7 — animated particle rate toward HQ).

## Known MVP gaps (by design, not bugs)

- **Life district has no streak/belt_speed.** `mcp__lungnote__list_todos` only gives current
  done/pending counts, not per-item completion timestamps — no way to compute "completed in last
  7 days" yet. Shows as a static (non-animated) line to HQ.
- **Personal todos are a manual snapshot**, not live. `export_state.py` reads
  `data/personal_todos_snapshot.json`, which has to be re-fetched (via the LungNote MCP tool) and
  overwritten by hand. A live path would mean giving this script its own Supabase client/creds —
  skipped for MVP to avoid a second copy of the LungNote service key.
- **HQ level is a stub.** Wiring real KPIs (webapp signups, revenue, tasks-merged/week) is next.

## Next phases

1. Wire HQ tier to real KPIs (CFO/KPI data already exists elsewhere in the org — reuse, don't rebuild)
2. Live personal-todo sync (either share LungNote's Supabase client, or add a small `sync` command
   that calls the MCP tool and overwrites the snapshot)
3. Idle-decay visual (belt dims/stops if a district has 0 completions in N days) — partially there
   via `belt_speed`, not yet visually distinct from "slow but alive"
