# Brief — Console `/flows`: the static Flow board (Control Room P2)

**For:** a developer in MoonieX-Console. **From:** CTO (winbox #7c33db60), 2026-10-02.
**Status:** G1 is done (MAC CTO #e6754203, 2026-10-02). The CEO approved the mockup and the
go-ahead the same day.
**Plan:** https://claude.ai/artifact/WkHh4MaagdambeWzNdJNMz (ClaudeFlow Control Room).

## Decided — where it lives (CEO 2026-10-02)

The CTO proposed `terminal.mooniex.com/flows` in the existing Console, reached over Tailscale with
the same passkey, with a fourth bottom-bar cell "Flow"; no new domain, nothing public. The CEO
answered "Ok". `terminal.mooniex.com` resolves to Contabo's tailnet IP (100.118.171.23, checked
2026-10-02), so this needs no DNS or proxy work.

## Mockup — approved (CEO 2026-10-02: "Ok ผ่าน ลุยได้")

- Canvas (the CEO's, private): https://claude.ai/artifact/9yjf3TosJWMeiu5Jw479ha. The source is in
  `docs/design/flows-board/mockup/` (Agents-Core): `Main.dc.html` = `/flows`, `Bl.dc.html` =
  `/flows/bl`. Its data are BL's export pasted in. The real pages fetch the API.
- Look = the Run Inbox page's, so the four tabs read as one app:
  - Colours: ground `#0d1419`, cards `#152029`, lines `#2a3a47`, text `#e3eaef`, muted `#97a6b2`.
  - Accents: teal `#5cc3cf` = auto, amber `#e3a74d` = agent or unknown cost, red `#f08a80` = a
    blocker that waits for the CEO.
  - Fonts: Chakra Petch, IBM Plex Sans Thai and IBM Plex Mono, which `run.html` already loads.
- The CEO took two changes from the first draft of this brief. Both are written into the items
  below:
  - A node's details open **inline under its row**, not in a bottom sheet.
  - The list also shows workflows that have **no flow.yaml yet**.

## What to build

Read-only pages. Nothing on them runs, retries or approves anything (run state is P3/P4).

1. **`GET /flows`** (`requireAuth`, `Cache-Control: no-store`, wired like `/run` in
   `src/routes/pages.js`; a `consoleMode === 'relay'` box skips it). One card per workflow:
   name, owner, trigger (`manual · CEO`), node count, auto % by steps, auto % by cost,
   cost per run, and how many nodes have no measured cost.
   - The card has a strip coloured by `effective_stage`, sized by node count, with its counts under
     it.
   - A live workflow with no flow.yaml gets a muted, dashed card that is not a link. It reads "ยังวาดไม่ได้
     เพราะยังไม่มี flow.yaml", with the F1 line under it.
2. **`GET /flows/<flow>`**: the graph of one workflow.
   - Phone (≤ 600 px): one row per `depth`, top to bottom; the nodes of a row sit side by side
     and wrap. Wider screens may turn rows into columns, left to right.
   - A node chip shows its `name`, its `kind`, its host, and its `last_cost_usd`, or `?` when that
     is null. Never show 0 for unknown.
   - Chip colour = `effective_stage` (`auto`, `auto_review`, `shadow`, `agent`, `human`). The
     legend sits on the page.
   - `release: true` nodes are marked.
   - A chip lists what it waits on ("รอ a · b") when that is not obvious: more than one `after`, or a
     row above with more than one node.
   - Tapping a chip opens its detail card **inline, right under that row**, and tapping it again
     closes it. One card is open at a time. Use a real `<button aria-expanded>`.
     - The card holds `does`, the latest measured cost, host, tool or role+skill or approver,
       provider/model, `unit_cost`, phase, `after`, `on_fail`, `verify`, `gate`, `blockers` and the
       `measured` list.
     - Blocker codes are red when they wait for the CEO (credit, login, key, quota, money, account)
       and orange otherwise.
   - A header carries the `stats` block.
3. **API**:
   - `GET /api/flows` and `GET /api/flows/:flow` (`requireAuthApi`).
   - Data comes from Agents-Core, never a copy: run `python3 <AGENTS_CORE>/scripts/flow-lint.py
     export <skill>` with `execFile` (no shell).
   - The list is `<AGENTS_CORE>/.claude/skills/*/flow.yaml`, plus the live workflows with no
     flow.yaml. Those are the `rule: "F1"` findings of `flow-lint.py check --json`.
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

- **Contabo's Agents-Core checkout** gained `scripts/flow-lint.py` and the BL workflow in the G1
  cutover (2026-10-02 04:56 TH, MAC CTO #e6754203). `flow-lint.py export CMO_Workflow_BlackLiquidity`
  there gives the numbers below. That checkout keeps local commits that are not pushed
  (`ahead 95`). Never pull, reset, stash or push it: it belongs to the sessions that run there. If
  it lacks something you need, tell the CTO.
- The real pages fetch the API. Tests run against fixture JSON made from `flow-lint.py export`.
- Workflow with a flow.yaml today: `CMO_Workflow_BlackLiquidity` only (flow `bl`).
  `CMO_Workflow_ShortFilm` has none yet (F1); the list must not break on it.
- A flow.yaml holds no secrets (rule F14), so the API may return it whole.

## Done when

- `/flows` lists BL. `/flows/bl` shows its 17 nodes in 13 rows (depth 0–12), and the header shows
  85.7 % auto by steps, 10.4 % auto by cost, $6.65 a run and 9 unknown. These are the export as of
  origin/main 3d091b3c; take the numbers from the export you run, not from this line.
- `/flows` also shows ShortFilm's muted card with no link, as long as ShortFilm has no flow.yaml.
- No horizontal page scroll at 390 px. Screenshots at 390 px go in REPORT.md: `/flows`, `/flows/bl`,
  and `/flows/bl` with the `editor` card open inline. Put them next to the mockup and name every
  difference.
- The bar has four cells on all four top-level pages, with the right cell active.
- vitest covers `/api/flows`: a fixture flow, an export failure, an unauthenticated request.
  `npm test` passes.
- Unauthenticated `GET /flows` redirects to login, like `/run`.

## Not in scope

Live run state and animation (P3/P4), the watcher and blocker alerts (P5), graduation (P6), editing a
flow from the UI. Deploying is the CTO's merge plus a Console restart. Tell the session owners on that
box before the restart.
