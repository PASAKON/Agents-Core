# Claude runs out last (IRON §59 rule 8): STATUS (PH #6c487e37, owner CTO Main cto-c34459eb)

Brief: `state/handoff/2026-10-15/brief-6c4-claude-runs-out-last.md` (Contabo). CEO 15 Oct. Budget $0.

| # | Milestone | State | Evidence |
|---|---|---|---|
| M1 | rank change, needs_claude_tool, plans, limit-stop hook | done | AGY Argon task-c7116818 (runner_fit redo), PH review; PR #343 merged @bcad5c73 |
| M2 | provider limit beats bonuses; dead codex/agy runs end failed | done | PR #346 merged @be89ab2a (asked by CTO Main 15 Oct) |
| M3 | merged + live-synced | done | card 0546; origin/main 0bdfb49d; Contabo live tree cd6db3b5 (11:19 TH) |
| M4 | E2E: real dev + CMO text job, runner/host/model_hint empty | done | see below |

## E2E (15 Oct, about 11:3x TH)
Pass line (CTO Main 03:16Z, option b): the `router:` line names an outside runner, not `claude:`.
- Dev, task-87baf87b (developer, S): `router: agy gemini-3.8-flash-high [agy-gemini] … ok`. Review: pass. PR #349.
- CMO text, task-592bef9a (content_strategist → doc_text, S): `router: agy gemini-3.8-flash-high [agy-gemini] … ok`. Review: pass. PR #350.

Live `route.py --plan developer --size M --host contabo` after the sync:
1. agy gemini-3.8-flash-high · agy-gemini 87.2% ok
2. agy gemini-4-argon-high · agy-gemini 87.2% ok (same bucket as Flash; Argon wins only its ties)
3. agy claude-sonnet-5-5-high · agy-claude 91% ok
4. claude claude-sonnet-5-5 · 45% → will_hit (reserve 50%)
5. codex · 0% · cannot: exhausted (weekly limit hit 09:33 TH, resets 20 Oct 05:27Z; the openai bonus is ignored)

content_strategist M: Flash, Argon, then Claude (will_hit).

## Open
- Codex: the CEO presses Full reset himself (Q-20261015-0240-661d). The router keeps Codex at `cannot` until a
  fresh Codex rollout exists. After his reset, one small `codex exec` writes it, then re-check route.py.

Blocker: none. Decided for CEO: none. Outcome: closed 15 Oct, 4/4.
