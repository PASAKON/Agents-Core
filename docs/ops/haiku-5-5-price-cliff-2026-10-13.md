# Haiku 5.5 100k price cliff — paid-API Claude call sites, measured (2026-10-13)

CEO order 13 Oct (relayed by SomPong): "อันนี้เป็นการใช้งาน haiku แบบประหยัดที่ถูกต้อง ให้ CTO ศึกษา
และปรับใช้กับองค์กรเราได้เลย". This doc covers the measured call-site list, the guards, the rule and
the Chatudo G0 re-estimate. Rule: ADR 0009 addendum 2026-10-13 (Agents-Rules) and
`CFO_Rules_Finance` principle 6.

**Labels.** **MEASURED**: read from logged usage, or counted from saved files and code.
**BOUND**: a ceiling derived from code limits, assuming each token covers at least 1 UTF-8 byte.
**ESTIMATE**: a computed guess, with its basis stated.

## 1. The price (checked 2026-10-13 on platform.claude.com/docs/en/about-claude/pricing)

Claude Haiku 5.5, $ per million tokens:

| Card | Input | Cache write 5 min | Cache write 1 h | Cache read | Output |
|---|---|---|---|---|---|
| request ≤ 100k input | 0.10 | 0.125 | 0.20 | 0.01 | 0.50 |
| request > 100k input | 0.50 | 0.625 | 1.00 | 0.05 | 2.50 |
| Batch, ≤ 100k / > 100k | 0.05 / 0.25 | — | — | — | 0.25 / 1.25 |

Pricing page, verbatim: "A request's prompt length counts all of its input tokens, including cache
reads and cache writes. Each request is priced on its own: a request over the threshold pays the
higher prices even when part of its prompt is a cache hit."

- Every other Claude 4.6+ model bills its full 1M window at one rate; Haiku 5.5 is the exception.
- Haiku 4.5 is flat at $1 / $5, and Sonnet 5.5 is flat at $2 / $10.
- The US-only `inference_geo` 1.1× also applies on top of the higher card.
- **Total input per request:**
  - Anthropic API: `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`.
  - OpenRouter: `usage.prompt_tokens`. `prompt_tokens_details.cached_tokens` is a breakdown of it
    (OpenAI schema). This is INFERRED: OpenRouter's docs do not state it.

**Tokenizer, MEASURED 2026-10-13.** The G0 system prompt (12,863 bytes, 4,993 chars, 79% Thai) costs
**4,238 Haiku 5.5 tokens**. That is 0.33 tokens/byte, or 0.85 tokens/char.

- Method: two `claude -p --model claude-haiku-5-5` calls on the subscription ($0), with and without
  the text, in both orders. The delta was 4,238 both times.
- Consequence: `chars / 4` under-counts Thai about 3.4×, so never size a Thai prompt that way.

## 2. Paid-API Claude call sites (every one goes through OpenRouter)

- A grep of Agents-Core, ClaudeFlow, Option, AlphaTrader, LineAutomation and Console found **no
  direct Anthropic API-key call**. The only hits were a test stub (`lunar-eval.js`), comments, and
  the OAuth usage endpoint (`cfo-claude-usage-feed.sh`, which is not a model call).
- Usage source: Supabase `webapp_cfo_api_events`, all time, `model ilike *claude*`: **2,007 rows,
  0 over 100k**, queried read-only on 2026-10-13.
- **Rows tagged `agent-run` / `webhook-reply` are per-turn sums** over the tool loop, so they are
  upper bounds on a single request.

| # | Call site | Model (live) | Size per request (input tokens) | Label | Guard |
|---|---|---|---|---|---|
| 1 | ClaudeFlow LuNar reply `src/webhook/claude.js` | `MODEL_LUNAR` = Kimi k2.6 (not Claude) | 161 turns, turn sum p50 30,333 / p95 81,188 / max 123,921 (Kimi tokens); system prompt 51,014 chars | MEASURED (`claudeflow_lunar_turns`) | cfo_track tag, per-request max |
| 2 | ClaudeFlow TaskMaster `agents/base.js` | Haiku 4.5 (default, env unset) | 1 turn: ≤ 31,720 | MEASURED (turn sum) | cfo_track tag, per-request max |
| 3 | ClaudeFlow SomPong agent `agents/base.js` | `MODEL_SOMPONG` = glm-5.2 (not Claude) | Sonnet 4.6 ×2 ≤ 16,321; Sonnet 5 ×1 ≤ 7,808 | MEASURED (turn sums) | cfo_track tag, per-request max |
| 4 | ClaudeFlow autogen ×3 (`autogen*.js`) | Sonnet 4.5, last run 2026-08-12 | max 5,412 (tradetech-content); others ≤ 3,282 | MEASURED | cfo_track tag |
| 5 | ClaudeFlow video `videoscript.js`, `videogen.js` | Sonnet 5 | scene-prompts 11 calls, max 2,967; script-write 3 calls, max 6,615 | MEASURED | cfo_track tag |
| 6 | ClaudeFlow `approval/refine.js` | Haiku 4.5 default | 0 rows (never ran); artifact text cut to 800 chars, plus the learned-rule list | BOUND (code) | cfo_track tag |
| 7 | ClaudeFlow `assist/draft.js` | Sonnet 4.6 default | no caller in `src/` or `scripts/`; no row | — | none: unreachable from a live route |
| 8 | ClaudeFlow manual scripts (`lunar-tester`, `lunar-e2e-test`, `lunar-eval`, `perf-lunar-*`, `seed-assist-examples`, `lunar-replay`) | Haiku 4.5 / Sonnet 4.6 | not logged | — | none: operator-run tests, covered by the rule (§4) |
| 9 | Option `trader/parser.js` (3 containers, up 3 weeks) | Haiku 4.5, `max_tokens` 200 | system 1,089 bytes + one Telegram message (≤ 4,096 chars ≈ 12.3 KB) → **≤ 13.4k** | BOUND (code + Telegram cap) | none: ≤ 13% of the cliff by construction, and Haiku 4.5 is flat |
| 10 | Agents-Core `tools/decide.py` OpenRouter provider | Haiku 4.5 | 2026-10 ledger on Contabo: 2 rows, both Jev (2,180); 0 OpenRouter-Claude calls | MEASURED (`state/decisions/2026-10.jsonl`) | ledger flag `prompt_cliff` |
| 11 | Agents-Core `scripts/trader_mindset_batch.py` | Sonnet 4.6 | caption prompt file ≤ 4,287 bytes, plus topic fields and an operator lessons file | BOUND (files) | none: manual batch, Sonnet is flat |
| 12 | Agents-Core `scripts/tm_prompt_eval.py`, `tm_prompt_evolve.py` | Claude 3.5 Sonnet | the files they read are ≤ 5,674 bytes each | BOUND (files, not request-exact) | none: manual, flat |
| 13 | Agents-Core `scripts/fusion_query.py` synthesizer | Sonnet 4 | question + N model answers; no log | not measured | none: manual CLI, flat, last changed 2026-07-12 |
| 14 | mooniex-webapp `news-brief-gen` (not on Contabo) | Haiku 4.5, last run 2026-09-10 | 862 calls (508 with tokens): p50 198 / max 212 | MEASURED | none: 0.2% of the cliff (follow-up: mirror the tag in `track.ts`) |
| 15 | mooniex-webapp `news-pipeline` | Haiku 4.5 / Sonnet 4.5 | Haiku 732 calls, p50 370 / max 443; Sonnet 216 calls, max 1,098 | MEASURED | same as #14 |

**Result:**
- The largest Claude request on record is ≤ 31,720 tokens.
- **No live job runs Haiku 5.5 today.** Every Haiku call is 4.5, which is flat-priced.
- So the cliff costs nothing now. The guards are there for the day a default moves to 5.5.
- The one prompt to watch is LuNar (#1).
  - Its 51k-char system prompt alone would be about 43k Haiku 5.5 tokens at the Thai ratio above.
    That is an ESTIMATE: it depends on the prompt's Thai share.
  - One of its turns already summed over 100k.
  - Before LuNar moves to Haiku 5.5, measure its per-request size on that tokenizer.

**Not paid per token, so out of scope** (Max subscription):
- every Claude Code role and worker;
- `claude -p` without `--bare`: secretary_server (its no-zai drop-in unsets the API keys),
  `mcp-borrow.sh`, cookierun_teachers T3, bl_scripter, rtk_ab;
- `/opt/claude-usage-monitor`;
- Chatudo G0's `claudeCliClient.js`, which never passes `--bare`.

## 3. Guards (log-only: none of them can block a request)

| Guard | Where | What it does | Blast radius |
|---|---|---|---|
| ClaudeFlow, task-4b1d7ace | `src/lib/cfo_track.js` `trackApiCall`, fed by the per-request max from `agents/base.js` and `claude.js` | Tags the CFO row `prompt_cliff: near` (≥ 80k) or `over` (> 100k), plus `cliff_max_request`; writes one `[price-cliff]` stderr line on `over` | Every ClaudeFlow call through `trackApiCall` (rows 1–6). Behaviour unchanged, return values unchanged, never throws. Live at the next image rebuild (the container runs a baked image built 2026-10-10). |
| Agents-Core, task-d4498b47 | `tools/decide.py` `decide()` | Sets `prompt_cliff` on the ledger row; writes one stderr line on `over` | Every `decide()` call. The `Decision` is unchanged. |

- Query for alerts: `webapp_cfo_api_events?tags->>prompt_cliff=eq.over`.
- No live customer chat is blocked; a blocking guard would need the CEO.
- Shas: see §6.

## 4. Context design that keeps a request under 100k

1. **Measure per request, never per turn.** A tool loop re-sends the whole prompt on every
   iteration, so cache reads count again each time.
2. Cap the history in bytes, not in turns. One long paste beats a turn cap.
3. Cut each tool result (G0 already cuts kb_search to 3 rows, and the judge snippets to 1,500 chars).
4. Long work goes to a sub-call that returns a summary. Never forward the raw transcript.
5. Cannot keep it under? Price the whole job at the > 100k card. Never average the two cards.

## 5. Chatudo G0, re-estimated on paper (Chatudo PARKED: no code changed, no job run)

- Old figure (`docs/briefs/chatudo-october-build.md`, ESTIMATE, not measured): about $0.004 per
  turn on a Flash-class model, so G0 ≈ $4.
- G0 today drafts and judges on the Claude Code CLI subscription ($0, `docs/chatudo/g0.md`).
  The figures below are for the API.
- Source: the saved run `2026-10-04-afterfix`. Bytes come from the pure prompt builders
  (`buildSystemPrompt`, `SHOP_TOOLS`, `buildJudgePrompt`), with the fixture shop profile.
- Script: `g0_cost.js`, read-only, kept in the CTO's scratchpad.

| Item | Value | Label |
|---|---|---|
| Drafts that ran the model | 194 of 200 | MEASURED |
| Tool calls | 206 (max 3 per draft) | MEASURED |
| Agent requests | ≤ 400 (tool calls + 1 per draft; `MAX_ITER` 4) | BOUND |
| Judge requests | 78 | MEASURED (saved score file) |
| Largest agent request | 67,968 bytes → **≈ 22,680 tokens** | MEASURED bytes × MEASURED ratio |
| Largest judge request | 20,554 bytes → ≈ 6,772 tokens | MEASURED bytes × MEASURED ratio |
| Ceiling for any G0 request (longest history + 4 rounds of the 3 largest KB rows) | 83,384 bytes, so **< 100k tokens even at 1 token/byte** | BOUND |
| Input for one full run | ≈ 2.71M tokens (agent 2.52M incl. 286 tool-system tokens/request, judge 0.19M) | ESTIMATE (measured bytes × ratio) |
| Output for one full run | ≈ 30k tokens with no thinking (draft text 14.6k, tool-call JSON ~12.4k, verdicts ~3k) | ESTIMATE |

**Cost of one 200-chat G0 run on Haiku 5.5 (ESTIMATE):**

| Thinking per request | ≤ 100k card (where G0 sits) | If wrongly priced at the > 100k card | Sonnet 5.5, for scale |
|---|---|---|---|
| none | **$0.29** | $1.43 | $5.72 |
| 500 tokens | $0.41 | $2.03 | $8.11 |
| 1,500 tokens | $0.64 | $3.22 | $12.89 |

- Every G0 request is under the cliff (BOUND), so G0 always bills on the ≤ 100k card.
- One run costs about $0.0015–0.0033 per chat, against the old ESTIMATE of $0.004 per turn.
  Under the $20 cap that is about 30–60 full runs (ESTIMATE). Seven G0 run folders exist since
  1 Oct, all on the CLI at $0.
- Caching the about 5k-token system prompt and tools would cut input further. It is not counted
  here: the minimum cacheable length for Haiku 5.5 was not checked.
- The pilot's live chat is **not measured**: it has not started (23 Oct).
  - The live shop agent loads **20** history messages, not G0's 6, so its requests run larger.
  - Keeping them under 100k needs a byte cap on history (design note only: Chatudo is PARKED).
- The quality question stays open. Whether G0 and the pilot may use the API under the $20 cap is
  the CEO's decision (LungNote, cto-4bb20df8; the G0 replay itself is due 2026-10-15). This doc
  does not make it.

## 6. Landed

Filled in at landing:
- ClaudeFlow guard: `<sha>`
- Agents-Core guard: `<sha>`
- This doc and the skill rule: `<sha>`
- ADR 0009 addendum (Agents-Rules): `<sha>`
