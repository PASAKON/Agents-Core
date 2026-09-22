# The decision layer — `tools/decide.py`

CEO ruling, 2026-09-22 (session cto-0e8d80b8, `research/2026-09-22-typesafe-jev-system-one-models.md`
in Agents-Wikis): anything a typed model does better/faster than an agent
"thinking it in context" becomes **a tool the agent calls**, chosen per job
by *measured tokens in/out*, never by speed. This document is that spec.

IRON §54: projects are independent. **ClaudeFlow / LungNote implement a thin
client to THIS spec — they do not import this repo's code.** Copy the yaml
schema and the ledger row shape; the provider ladder and budget logic are
each project's own to re-implement against its own env vars and ledger
location.

## What a decision site is

A *decision site* is one declared, fixed-schema question — never open-ended
generation. "What state is this page in?" is a site; "write me a caption"
is not. Each site is one YAML file, `config/decisions/<site>.yaml`, named
after the file's own `site:` field (dotted, e.g. `browser.page_state`).

A site is never invented ad hoc from inside code — `tools/decide.py` refuses
`decide()` for any site name that has no yaml file. This is deliberate: the
option set, the rules, and the counterfactual basis are all reviewable in
one file, in git, instead of scattered across whichever script needed a
quick classification.

## YAML schema

```yaml
site: browser.page_state          # must match the filename (browser.page_state.yaml)
question: "What is the current state of the page?"
max_state_chars: 2000             # state is truncated to this before any LLM call
provider_policy: rules-then-llm   # rules-only | rules-then-llm
options:                          # <= 255 total (Jev's cardinality cap)
  - id: idle
    meaning: "Nothing in flight."
  - id: generating
    meaning: "A job is queued or rendering."
rules:                            # regex table, tried top to bottom, first match wins
  - pattern: 'generating|in queue'
    option: generating
counterfactual:
  images: 1                       # screenshots this decision would have cost in-context
  big_model_tokens_out: 20        # output tokens the big model would have spent
  extra_input_chars: 0            # optional: fixed per-call overhead (e.g. a large
                                   # system prompt resent every call) not part of `state`
```

Two fields make the option set/rules **dynamic** instead of a static list
(used by `skill.route.yaml`, whose option set is "every org skill" and
would drift the moment it was copied into a yaml):

- `options_source: skills_dir` + `skills_dir: <path>` — options are loaded
  from every `<path>/*/SKILL.md` frontmatter (`name` -> option id,
  `description` -> option meaning) at call time.
- `rules_source: skill_description` — rules are built from each skill's own
  frontmatter description's `"Trigger on X, Y, Z."` clause, extracted
  verbatim (`tools/decide.py`'s `extract_trigger_patterns()`), never
  re-typed by hand.

Validation (`load_site()`) refuses: a missing `question`, an invalid
`provider_policy`, zero resolved options, or more than 255 resolved
options — loudly, before any ledger row is written.

## Ledger row schema

Append-only JSONL, one file per calendar month:
`state/decisions/<YYYY-MM>.jsonl` (gitignored — runtime state, never source).
**Every `decide()` call writes exactly one row, whatever the outcome** —
including a refused/failed call, so nothing is lost silently.

```json
{
  "ledger_id": "ab12cd34ef56ab78",
  "ts": "2026-09-22T14:10:38+00:00",
  "site": "browser.page_state",
  "provider": "rules",
  "choice": "moderated",
  "probs": {"moderated": 1.0},
  "calibrated": true,
  "tokens_in": 0,
  "tokens_out": 0,
  "cost_usd": 0.0,
  "latency_ms": 0.4,
  "state_chars": 42,
  "counterfactual_usd": 0.0122,
  "counterfactual_basis": "ESTIMATE: fable-5.1 counterfactual = ...",
  "session_id": "cto-0e8d80b8",
  "task_id": "task-2a29d27e",
  "error": null
}
```

`session_id`/`task_id` are read from `CXO_SESSION_ID`/`CTO_SESSION_ID` and
`WORKER_TASK_ID` respectively — the same env vars skill telemetry already
tags events with — never passed explicitly by a caller.

## Provider ladder + budget rule

```
rules-only      -> [rules]
rules-then-llm  -> [rules, openrouter, jev]
```

1. **rules** — a regex table from the site's own yaml. Free, always on,
   tried first. A hit returns `probs={<option>: 1.0}`, cost 0.
2. **openrouter** — Haiku 4.5 via OpenRouter, self-reported (not calibrated)
   confidence. Gated OFF by default — requires **all three**:
   `OPENROUTER_API_KEY` set, `DECIDE_PROVIDER=openrouter` set (an explicit
   opt-in switch, independent of the key), and the monthly ledger spend
   (`lib/decision_ledger.month_paid_cost_usd()`) plus this call's estimated
   cost staying under `DECIDE_BUDGET_USD` (env, **default 0 — paid calls
   disabled**). Going over budget raises `ProviderUnavailable` with a
   `decision_budget_refused: ...` message, which the ladder catches and
   which lands in that row's `error` field — so a refusal is itself a
   logged, auditable outcome, not silence.
3. **jev** — TypeSafe's Jev, `calibrated: true`. Requires `JEV_API_KEY`
   (early access / waitlist as of 2026-09-22) **and** `JEV_API_URL` (the
   vendor's API is referenced, not detailed, at launch — this code refuses
   to invent an endpoint). Missing either raises `ProviderUnavailable`
   cleanly.

A provider that actually *ran* (even to a `choice: null` — bad JSON, an
off-schema answer) stops the ladder right there: falling through to the
next paid provider would silently spend twice for one decision. Only a
provider that never ran at all (gated off, no key, over budget) lets the
ladder continue to the next rung.

**Nothing here spends money unless an operator has explicitly turned a paid
provider on.** A `decide()` call with no env configured resolves entirely
through free rules (or `choice: null` on a `rules-only` site with no match)
— this mirrors the org's standing "ask before paid API" rule at the code
level, not just as a habit to remember.

## The cost rule, in one formula

```
counterfactual_usd = ((state_chars + extra_input_chars)/4 + images*814) * price_in(fable-5.1)
                    + big_model_tokens_out * price_out(fable-5.1)
```

Prices come from `config/decisions/_providers.yaml` (`counterfactual.claude-fable-5-1`),
never hardcoded — the report's "saved" column is `counterfactual_usd - cost_usd`,
and `report`'s header explicitly labels `counterfactual_usd` an **ESTIMATE**
(CEO rule: never launder an estimate as measured data).

**The two facts that make this the right formula to optimize:**

1. **The cost is in the input STATE size, not the question.** A typed
   decision's own tokens are near-zero (schema + a short answer); what a
   browser_operator actually pays for is re-deriving "what is this page's
   state" from a screenshot (814 tokens at the skill's standard 1024x591
   viewport) every time it looks. Extract the *smallest sufficient* state
   with `javascript_tool`/DOM (a button's `innerText`, a card's message)
   before ever calling `decide()` — passing a screenshot's worth of text
   defeats the entire point.
2. **Anything answered inside a long session is re-sent every later turn.**
   A screenshot or a paragraph of reasoning that entered context at turn 3
   is billed again at every turn after it, for the rest of the session
   (`browser-operator` SKILL.md § "The number that governs every decision").
   A `decide()` call is a single external round-trip that leaves nothing
   in the agent's own context except the answer — it does not compound.

## How to add a site

1. Write `config/decisions/<name>.yaml` — `site`, `question`, `options`
   (or `options_source`), `max_state_chars`, `provider_policy`, `rules`
   (or `rules_source`), `counterfactual`.
2. `python tools/decide.py sites` should list it; `load_site(name)` should
   not raise.
3. Add a rules-provider test case (a piece of real, measured state text ->
   expected option) before ever turning on a paid provider for it.
4. If the site will ever run `rules-then-llm`, decide `DECIDE_BUDGET_USD`
   with the CFO/CEO first — the default (0) is intentional and safe.

## What must never go through `decide`

- **Open-ended generation** — captions, prompts, dialogue, code. Jev/System
  One models give up string generation entirely; there is no free-text
  output to ask for.
- **Anything needing an image.** Jev takes no images "(yet)" per the
  vendor's own post. Visual judgment (does this frame look right, is this
  chip bound) stays on the org's runners/vision path, not this tool.
- **A per-prompt hook that could ever need a paid call.** `skill.route.yaml`
  is `provider_policy: rules-only` for exactly this reason — a hook that
  fires on every prompt must never have a code path that reaches for money.

## Jev status (2026-09-22)

Early access, waitlist (`console.typesafe.ai/playground`). API is
"referenced, not detailed" in the vendor's own launch post — no documented
request/response shape, no confirmed endpoint URL. `tools/decide.py`'s jev
provider implements the shape the article *describes* (POST state + schema,
get back per-option probabilities) but reads the endpoint from
`JEV_API_URL` rather than inventing one, and raises `ProviderUnavailable`
cleanly without a key. Treat every number attributed to Jev in this repo as
unverified until real access lands — re-check pricing, cardinality cap, and
image support against `research/2026-09-22-typesafe-jev-system-one-models.md`'s
`refresh_after: 2026-10-22` date.

## The `report` verb

```
python tools/decide.py report [--month 2026-09]
```

Prints one row per site for the month: call count, provider mix (e.g.
`rules:40,openrouter:2`), tokens in/out, `cost_usd`, `counterfactual_usd`
(labelled ESTIMATE in the header), and `saved_usd` (`counterfactual - cost`).
Backed by `lib/decision_ledger.summarize_month()`, which reads the raw JSONL
— there is no separate aggregate store to fall out of sync.
