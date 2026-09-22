# task-a6129a75 — real Jev/OpenRouter decisions API

## Files
- `tools/decide.py` — `_jev_provider` rewritten against the measured endpoint
  (`POST https://openrouter.ai/api/alpha/decisions`, Bearer `OPENROUTER_API_KEY`);
  added `_env`/`_provider_gate`/`_jev_model_id`/`_jev_price_in`/`_response_error_text`;
  ladder reordered `rules -> jev -> openrouter`; budget gate now also covers jev;
  `extra` field added to the ledger row (carries jev's `confidence`).
- `config/decisions/_providers.yaml` — added `openrouter."typesafe/jev-1.13"`
  (measured price); marked the old guessed `jev.system-one` entry superseded
  (kept, not deleted, per the task brief's "keep the rest").
- `tests/test_decide.py` — removed 2 tests that asserted the guessed
  `JEV_API_KEY`/`JEV_API_URL` adapter's behavior (dead code path once the
  real endpoint landed); added 13 new tests (fixture-based jev success,
  400 zod-error fallthrough vs jev-only choice=None, ladder selection per
  `DECIDE_PROVIDER`, `.env` fallback incl. tmp-file + empty-counts-as-absent,
  budget gate summing jev spend, the new `_providers.yaml` entry).
- `tests/fixtures/jev_decisions_response.json` — new, verbatim measured response.

Did not touch `config/decisions/browser.*.yaml`, `config/decisions/sompong.route.yaml`,
`config/decisions/skill.route.yaml`, or `docs/design/decision-layer.md` (T2's files).

## Tests
- `pytest tests/test_decide.py -p no:warnings -q` → **40 passed** (was 28; net
  +12 after removing 2 and adding 14 — see above).
- `pytest scripts/ tests/ --import-mode=importlib -p no:warnings --ignore=scripts/test_skill_doctrine_lint.py`
  → **1436 passed, 18 skipped** (≥1427 required).
- `python tools/decide.py report` after the live smoke shows the jev row,
  provider `jev`, calibrated `true`.

## Live smoke (ran ONCE, from the real `.env`)
```
DECIDE_LIVE=1 python tools/decide.py browser.page_state --state-file <refusal text> --provider jev
```
Ledger row (`state/decisions/2026-09.jsonl`, gitignored — not committed):
```json
{
  "ledger_id": "3287cf23a7e24380",
  "ts": "2026-09-22T15:26:51+00:00",
  "site": "browser.page_state",
  "provider": "jev",
  "choice": "moderated",
  "probs": {"idle": 0, "generating": 0, "done": 0, "moderated": 1,
             "rate_limited": 0, "signed_out": 0, "error": 0, "unknown": 0},
  "calibrated": true,
  "tokens_in": 538,
  "tokens_out": 81,
  "cost_usd": 2.2596e-05,
  "latency_ms": 1125.93,
  "extra": {"confidence": 1},
  "counterfactual_usd": 0.0094425,
  "error": null
}
```
Cost $0.0000226, well inside the $5/mo `DECIDE_BUDGET_USD`. No key printed anywhere
(this output, logs, or tests).

## Doc paragraph for `docs/design/decision-layer.md` (CTO to fold in — I did not
touch that file, it's T2's)

Replace the "## Provider ladder + budget rule" section's ladder order and
jev description with:

> Provider ladder per `provider_policy`:
> ```
> rules-only      -> [rules]
> rules-then-llm  -> [rules, jev, openrouter]
> ```
> `DECIDE_PROVIDER` names the highest paid rung an operator has turned on:
> unset/`rules` → no paid rung runs; `jev` → jev only; `openrouter` → jev,
> then openrouter/haiku if jev errors. Jev runs first because it's ~25x
> cheaper on input, free on output, and calibrated by construction.
>
> **jev** — TypeSafe's Jev, live on OpenRouter (measured 2026-09-22,
> `research/2026-09-22-typesafe-jev-system-one-models.md`): `POST
> https://openrouter.ai/api/alpha/decisions`, `Authorization: Bearer
> OPENROUTER_API_KEY` (same key as the openrouter/haiku rung — Jev is served
> over OpenRouter, not a separate TypeSafe endpoint). `calibrated: true`.
> Any non-200 response or an off-schema answer (`answers.<site>` missing
> `choice`/`probabilities`) raises `ProviderUnavailable` with the server's
> message and falls through to openrouter/haiku (if `DECIDE_PROVIDER=openrouter`)
> — never a guessed choice. `cost_usd` is `usage.cost` from the response
> (exact) when present, else the `_providers.yaml` price-table estimate.
> Model id defaults to `typesafe/jev-1.13`, overridable via `DECIDE_JEV_MODEL`.
>
> Remove the old "## Jev status (2026-09-22)" section's "no confirmed endpoint
> URL" language — it's now confirmed and live; the endpoint URL, request/response
> shape and pricing above are all measured, not vendor-claimed.

## Blockers
- None. All 6 deliverables shipped; acceptance criteria met (see Tests above).

## Skill learning
- MISSING [dev-spawn-protocol §env-sharing]: this task's worktree branched off
  local `main` (`d4a48228`) which was 8 commits **behind** local `main`'s actual
  tip (`721ad1b2`) — including T1's own `tools/decide.py` this task depends on —
  because `origin/main` on GitHub hadn't been pushed past `d4a48228` yet while
  local `main` had already absorbed several merges. `git merge main` (the local
  branch, not `origin/main`) fixed it. A spawn brief that says "T1 merged
  `cb560f75`" should tell the DEV to `git merge main` (local) if the file isn't
  there yet, rather than the DEV discovering via a full `find`/`glob` miss.
  evidence: task-a6129a75, `git log --oneline HEAD..main` showed 8 commits.
- WRONG [no owner — test isolation]: adding an env-var-or-.env fallback helper
  (`_env()`) to a tool, without also neutralizing the `.env` fallback path (not
  just `os.environ`) in the test suite's autouse fixture, let 2 pre-existing
  tests that assert "no key set" fall through to the real gitignored `.env`
  and make live paid API calls (~$0.00002 x2) during routine `pytest` runs —
  before I'd even started the live-smoke work. Any future `os.environ.get(X)
  or _read_dotenv_var(X)` pattern needs its test fixture to monkeypatch the
  `_read_dotenv_var` reference too, not just `monkeypatch.delenv`. evidence:
  task-a6129a75, first `pytest tests/test_decide.py` run after adding `_env()`.
  fix: `monkeypatch.setattr(decide_mod, "_read_dotenv_var", lambda name: None)`
  in the autouse fixture — now in `tests/test_decide.py`.
- COSTLY [no owner]: confirming which `main` (local vs `origin/main`) actually
  had T1's files ate the most time in this task — `git status` said "up to
  date with origin/main" while local `main` was 8 commits ahead of the fetched
  `origin/main`, because this worktree's upstream tracking ref is
  `origin/main`, not local `main`. prevented by: check `git rev-parse main`
  vs `git rev-parse origin/main` vs `git rev-parse HEAD` explicitly instead of
  trusting `git status`'s "up to date" line, whenever an expected merged file
  is missing.
