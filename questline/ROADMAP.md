# Questline — Roadmap

## Related prior art (read this first)

`mooniex-webapp` already has a live Godot 3D tycoon at `/admin/tycoon`: cars=tools,
roads=API lines, destinations=world markets (TikTok/YT/FB), meters=views+buyers,
top-down Cities:Skylines camera, real automation-event + cost data fed in via a
postMessage bridge. CEO later pulled the *ops-monitoring* job away from it to a
plain 2D SVG tool (`/admin/workflows`) — Godot/WASM/iframe was too heavy for a
job that's really just "line + dot + text + box." The Godot tycoon stays up only
as a showpiece.

Questline is not that project. It's about **your** work (dev/growth tasks +
personal life), not content distribution. But it's the same genre, and the
lesson transfers directly: stay web/2D, don't reach for a game engine. That's
why Questline is a single `index.html` + canvas, no build step, no WASM.

## How it works today (Phase 1+2 — done)

```
state/tasks.db ─┐
                ├─> export_state.py ─> state.json ─> index.html (canvas)
personal_todos_snapshot.json ─┘
```

- `export_state.py` — stdlib-only Python. Queries `tasks.db` for role/status/
  updated_at, splits into two districts by role:
  - **dev**: developer, web_designer, backend_dev, frontend_dev, devops_engineer,
    tester, qa, security_engineer
  - **growth**: content_strategist, ads_manager, prompt_engineer, data_analyst
  - **life**: read from `data/personal_todos_snapshot.json` (manual LungNote
    snapshot — see gaps below)
  - Per district: `completed`, `backlog`, `tier` (1-5 from completed count),
    `belt_speed` (completions in last 7 days ÷ 7)
- `index.html` — fetches `state.json`, draws each district as a row of buildings
  (count = tier, height increases per building), backlog as stacked crates
  (capped at 20 drawn), and animates small particles from each district toward
  a central HQ tower at a rate proportional to `belt_speed`.
- `HQ` — stubbed at level 1. Meant to level up from real org KPIs, not wired yet.

Verified: ran against real data (209 dev tasks done / 16 backlog, 12 growth done,
35 personal done / 119 backlog), rendered via headless Chrome screenshot —
buildings, crates, and belt particles all draw correctly.

## Known MVP gaps (called out, not hidden)

1. **Life district has no streak.** `list_todos` gives current done/pending
   counts, not per-item completion timestamps — can't compute "completed in
   last 7 days" for personal tasks yet.
2. **Personal snapshot is manual**, not live — has to be re-fetched via the
   LungNote MCP tool and the JSON overwritten by hand.
3. **HQ is a stub** — no real KPI wired in yet.

## Roadmap

**Phase 3 — HQ real-KPI wiring (next)**
Options, in order of how much they reuse existing infra:
- (a) **Reuse `/api/office/automation-events`** (already live, already
  admin-gated, already real — the same endpoint the Godot tycoon reads) as an
  additional "Distribution" district or as HQ fuel. Zero new schema.
- (b) Pull 2-3 numbers already tracked for CFO/KPI reporting (signups,
  revenue, tasks-merged/week) via the existing wiring those skills already
  document, rather than querying Supabase fresh.
- Recommendation: (a) first — it's a single fetch, already proven live, and
  keeps Questline and the tycoon reading from the same source of truth instead
  of two parallel KPI pipelines.

**Phase 4 — Live personal-todo sync**
Either give `export_state.py` its own Supabase client (reuses the LungNote
service key already in `mcp/lungnote-mcp/.env` — same key, no new secret), or
add a `questline sync` command that just calls the MCP tool and overwrites the
snapshot. Needed before Life district can get a real streak/belt_speed.

**Phase 5 — Idle-decay visual**
Belt dims/stops when a district has had 0 completions for N days — right now
`belt_speed` can already hit 0, but it's not visually distinct from "slow."
Small CSS/canvas change, no new data needed.

**Not planned (scope fence, matches the tycoon lesson):**
- No 3D, no game engine, no WASM bundle, no iframe embed into webapp.
- No fabricated numbers — if a metric isn't tracked (e.g. personal-task
  streaks, right now), it stays visibly absent/stubbed rather than faked.
