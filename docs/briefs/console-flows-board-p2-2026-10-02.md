# Brief — Console `/flows`: the static Flow board (Control Room P2)

**For:** a developer in MoonieX-Console. **From:** CTO (winbox #7c33db60), 2026-10-02.
**Hold:** do not delegate before MAC CTO #e6754203 announces "G1 done".
**Plan:** https://claude.ai/artifact/WkHh4MaagdambeWzNdJNMz (ClaudeFlow Control Room).

## Decided — where it lives (CEO 2026-10-02)

The CTO proposed `terminal.mooniex.com/flows` in the existing Console, reached over Tailscale with
the same passkey, with a fourth bottom-bar cell "Flow"; no new domain, nothing public. The CEO
answered "Ok". `terminal.mooniex.com` resolves to Contabo's tailnet IP (100.118.171.23, checked
2026-10-02), so this needs no DNS or proxy work.

## What to build

Read-only pages. Nothing on them runs, retries or approves anything (run state is P3/P4).

1. **`GET /flows`** (`requireAuth`, `Cache-Control: no-store`, wired like `/run` in
   `src/routes/pages.js`; a `consoleMode === 'relay'` box skips it). One card per workflow:
   name, owner, trigger (`manual · CEO`), node count, auto % by steps, auto % by cost,
   cost per run, and how many nodes have no measured cost.
2. **`GET /flows/<flow>`**: the graph of one workflow.
   - Phone (≤ 600 px): one row per `depth`, top to bottom; the nodes of a row sit side by side
     and wrap. Wider screens may turn rows into columns, left to right.
   - A node chip shows its `name`, its `kind`, its host, and its `last_cost_usd`, or `?` when that
     is null. Never show 0 for unknown.
   - Chip colour = `effective_stage` (`auto`, `auto_review`, `shadow`, `agent`, `human`). The
     legend sits on the page.
   - `release: true` nodes are marked.
   - Tap a chip to open a sheet with `does`, tool or skill or approver, provider/model,
     `verify`, `gate`, `blockers`, `on_fail` and the `measured` list.
   - A header carries the `stats` block.
3. **API**:
   - `GET /api/flows` and `GET /api/flows/:flow` (`requireAuthApi`).
   - Data comes from Agents-Core, never a copy: run `python3 <AGENTS_CORE>/scripts/flow-lint.py
     export <skill>` with `execFile` (no shell).
   - The list is `<AGENTS_CORE>/.claude/skills/*/flow.yaml`.
   - Cache per skill on the flow.yaml mtime.
   - Add `AGENTS_CORE_DIR` to `src/config.js` (default `/opt/MoonieXHQ/Agents/Core`).
   - When an export fails, the card shows the error line instead of hiding the workflow.
4. **Bottom bar**: add the fourth cell `{key: 'flows', href: '/flows', label: 'Flow'}` in
   `public/js/nav.js`.
   - The rules of docs/design/run-inbox/DESIGN.md §12 still hold (Agents-Core repo): the whole cell
     is the button, 56 px tall, icon plus one word. That leaves about 97 px a cell on a 390 px
     phone.
   - Thumbs come first: no target under 44 px, terse Thai copy.

## The contract you read

`flow-lint.py export` prints one JSON object:
- Top-level keys: `schema flow name skill owner goal output host trigger watcher budget phases
  nodes edges stats`.
- Each node carries the flow.yaml keys plus `order`, `depth`, `effective_stage` and
  `last_cost_usd`.
- `edges` is `[[from, to], …]`.
- `stats` is `{nodes, auto_pct_steps, cost_per_run_usd, auto_pct_cost, cost_unknown}`.

The meaning of every field is in `.claude/skills/ALL_Protocol_SkillAuthor/references/workflow-flow.md`
(§8 how the board reads it, §9 computed values). Draw what the export says. Do not compute auto %
or cost again in JS.

## Known before you start

- **Contabo's Agents-Core checkout has no `scripts/flow-lint.py` yet.** On 2026-10-02 it read
  `main...origin/main [ahead 94, behind 8]` with a dirty file. Do not pull, reset or stash it: that
  checkout belongs to the sessions that run there. Tell the CTO, who gets it synced. Until then,
  build and test against fixture JSON made from `flow-lint.py export` on a fresh clone.
- Workflow with a flow.yaml today: `CMO_Workflow_BlackLiquidity` only (flow `bl`).
  `CMO_Workflow_ShortFilm` has none yet (F1); the list must not break on it.
- A flow.yaml holds no secrets (rule F14), so the API may return it whole.

## Done when

- `/flows` lists BL. `/flows/bl` shows its 17 nodes in 13 rows (depth 0–12), and the header shows
  85.7 % auto by steps, 10.4 % auto by cost, $6.65 a run and 9 unknown. These are the export as of
  origin/main 3d091b3c; take the numbers from the export you run, not from this line.
- No horizontal page scroll at 390 px. Screenshots of `/flows`, `/flows/bl` and one open node sheet
  at 390 px go in REPORT.md.
- The bar has four cells on all four top-level pages, with the right cell active.
- vitest covers `/api/flows`: a fixture flow, an export failure, an unauthenticated request.
  `npm test` passes.
- Unauthenticated `GET /flows` redirects to login, like `/run`.

## Not in scope

Live run state and animation (P3/P4), the watcher and blocker alerts (P5), graduation (P6), editing a
flow from the UI. Deploying is the CTO's merge plus a Console restart. Tell the session owners on that
box before the restart.
