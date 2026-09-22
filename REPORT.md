# task-3de56f59 — SomPong routing via decide()

## What changed

`run_secretary_turn` (runners/secretary_server.py) now calls
`decide("sompong.route", prompt)` before any `claude` subprocess and picks
a lane from the confident outcome (mirrors `tools/flow_shoot.py`'s
`_decision_is_confident` money-guard: act only on `provider == "rules"` or
`probs[choice] >= 0.9`):

| outcome (confident only) | lane |
|---|---|
| `chitchat` | **light** — new `PROFILE_LIGHT`: `claude -p --model claude-haiku-4-5`, `--tools ""`, `--strict-mcp-config` with no `--mcp-config`, `--max-turns 1`, no `--resume` |
| `spam`, profile `claude-code-family` | **silent** — fixed `SPAM_REPLY_TEXT`, `_run_claude_once` never called |
| `spam`, profile `secretary` | full lane (the CEO is never spam) |
| `order_for_cto` / `order_for_other_cxo` / `question` | full lane, unchanged |
| not confident / `choice: null` / `decide()` raises | full lane |

Kill switch `SOMPONG_ROUTE=off` (env/`.env`, via `tools.decide._env`) skips
`decide()` entirely and forces the full lane. Default on.

Light-lane usage (`input_tokens`/`output_tokens` from the claude JSON
result, if present) is logged via `lib.db.log_event(kind="sompong_lane")`,
best-effort (a DB hiccup never fails the turn).

## Call chain (Gate 4b)

`Handler.do_POST` → `run_secretary_turn` → `decide_tool.decide("sompong.route", prompt)`
→ lane → `_run_claude_once(prompt, session_id, profile, lane)`. Confirmed by
grep: `decide_tool.decide("sompong.route", prompt)` sits at
`runners/secretary_server.py:1336`, textually inside `run_secretary_turn`
(not only in tests).

## Files Changed

- `runners/secretary_server.py` — lane selection inlined in
  `run_secretary_turn`; `PROFILE_LIGHT`/`LANE_FULL`/`LANE_SPAM_SILENT`
  constants; `SPAM_REPLY_TEXT`; two ≤600-char light-lane system prompts
  (`LIGHT_SYSTEM_PROMPT_FAMILY`/`_SECRETARY`); `_decision_is_confident`;
  `_log_light_lane_usage`; `_build_claude_cmd`/`_run_claude_once` take a
  `lane` param (light lane is an early-return branch, full lane unchanged).
- `config/decisions/sompong.route.yaml` — added rules (see "Rules added"
  below).
- `scripts/test_secretary_server.py` — autouse fixtures sealing decide()'s
  paid vars/dotenv fallback and redirecting the decision ledger (this file
  is outside `tests/conftest.py`'s coverage); fixed the `running_server`
  stub's signature for the new `lane` arg; 5 new tests (light-lane argv x2,
  system-prompt length, `model: "light"` rejected at both layers).
- `tests/test_sompong_route.py` (new) — 20 tests: the full routing matrix,
  session-continuity, ledger-row, and usage-telemetry tests (see Tests).
- `docs/ops/sompong-routing-decide.md` (new, 60 lines) — lane table, kill
  switch, how to read the numbers, Contabo deploy steps (not run).

## Rules added to `config/decisions/sompong.route.yaml`, and why each is safe

1. `^\[C-LEVEL DIGEST\]` → `order_for_cto`. **Not explicitly requested by
   the brief** — added because `runners/secretary_waker.py`'s digest turn
   is the only caller anywhere in the codebase that ever sends this literal
   marker (always profile=`secretary`). The existing "spam,
   profile=secretary → full lane" rule already protects it from the silent
   lane, but not from a confident `chitchat` verdict, which routes to the
   light lane regardless of profile and would silently break the digest
   summary. Free, deterministic, first in the list, zero false-positive
   risk (nothing else emits this string). Verified with a round-trip
   PyYAML + `re` test against the real digest text shape before committing.
2. Thanks/ok/555/pure-emoji → `chitchat`, all anchored `^...$` over the
   *whole* message. Verified live that "ขอบคุณครับ แล้วช่วยทำ X ให้หน่อย"
   does **not** match (falls through to the LLM rung / full lane) — a
   substring match would have been unsafe.
3. Bare URL (`^https?://\S+$`) → `spam`. Safe on both profiles: on
   `secretary` the "never treat the CEO as spam" rule wins regardless; on
   `family` a wrong call just means a neutral reply instead of engaging the
   link. Deliberately did **not** try to detect "unknown sender" (the
   brief's own example phrase) — that's not part of the state text this
   site ever receives, so a rule claiming to check it would be
   undefendable. Also skipped a sticker-specific rule: no verified
   placeholder-text convention for LINE stickers exists anywhere in this
   repo or in claudeflow (a separate project, IRON §54), so guessing one
   would violate "when in doubt add NO rule."

All five new rules were round-trip tested (PyYAML load + `re.search`)
against representative strings, including negative cases, before being
committed — transcript below.

```
OK        text='[C-LEVEL DIGEST]\nจดหมายจาก C-level 1 ฉบับ:'           matched='order_for_cto'
OK        text='ขอบคุณครับ'                                            matched='chitchat'
OK        text='ขอบคุณครับผม'                                          matched='chitchat'
OK        text='โอเคครับ'                                              matched=None   (not in the whitelist, by design)
OK        text='โอเค'                                                  matched='chitchat'
OK        text='555555'                                                matched='chitchat'
OK        text='😀👍'                                                    matched='chitchat'
OK        text='https://example.com/x'                                 matched='spam'
OK        text='ดูอันนี้ด้วย https://example.com/x'                    matched=None
OK        text='ขอบคุณครับ แล้วช่วยทำ X ให้หน่อย'                      matched=None   (contains a thanks, but not PURE chitchat)
```

## Hand-run transcript (real `decide()`, stubbed `_run_claude_once`)

```
=== message 1: order (CEO -> CTO) ===
text: 'สั่งงาน CTO ให้แก้บั๊ก deploy script ด้วย'  profile: 'secretary'
secretary: sompong_route: order_for_cto -> full lane (profile=secretary, provider=rules)
-> lane: full
-> reply: '[stubbed reply, lane=full]'

=== message 2: chitchat (thanks) ===
text: 'ขอบคุณครับ'  profile: 'secretary'
secretary: sompong_route: chitchat -> light lane (profile=secretary, provider=rules)
-> lane: light
-> reply: '[stubbed reply, lane=light]'

=== message 3: bare URL, family profile ===
text: 'https://example.com/weird-link'  profile: 'family'
secretary: sompong_route: spam -> silent reply, no model call (profile=family, provider=rules)
-> lane: spam_silent (no _run_claude_once call)
-> reply: 'รับทราบครับผม'
```

`python tools/decide.py report` after this run (real, gitignored
`state/decisions/`, free `rules` provider only, $0 cost):

```
decision report 2026-09 (counterfactual_usd is an ESTIMATE, see config/decisions/_providers.yaml)
site	calls	provider_mix	tokens_in	tokens_out	cost_usd	counterfactual_usd	saved_usd
sompong.route	3	rules:3	0	0	0.0000	0.1304	0.1304
```

## Deploy

**Not run.** Contabo's `mooniex-secretary` systemd service is untouched;
`DECIDE_PROVIDER` is unset there, so until someone deploys, `decide()`
resolves through the free `rules` rung only and nothing about live traffic
changes. Steps are in `docs/ops/sompong-routing-decide.md` (env-file keys
added by the CTO/CEO by hand, `git pull` + `systemctl restart
mooniex-secretary`).

## Tests

- ran: `pytest scripts/ tests/ --import-mode=importlib -p no:warnings --ignore=scripts/test_skill_doctrine_lint.py`
- passed: 1504
- failed: 0
- skipped: 18
- (main before this task: 1482 passed / 15 skipped — this task adds exactly
  25 new tests: 5 in `scripts/test_secretary_server.py`, 20 in the new
  `tests/test_sompong_route.py`; the +3 skip delta vs. the brief's quoted
  1482/15 baseline predates this task, from T1/T1b/T2 already merged onto
  this branch's base per `git log`)

`tests/test_sompong_route.py` covers: rules/p=0.95/p=0.6/choice=None/
decide()-raises/`SOMPONG_ROUTE=off` → lane; family-spam silent reply with
`_run_claude_once` asserted never called; secretary-spam → full lane;
order_for_cto/order_for_other_cxo/question → full lane (byte-for-byte
prompt/profile forwarded); light lane never resumes an existing session and
never persists its own; a real `decide()` call writes one ledger row per
message; `sompong_lane` usage event logged only for the light lane (with
tokens_in/out) and fails open on a DB error; `_decision_is_confident`
parity with `tools/flow_shoot.py`'s copy of the same gate.

`scripts/test_secretary_server.py` covers: light-lane argv (haiku model, no
`--mcp-config`, `--strict-mcp-config`, `--max-turns 1`, no `--resume`, zero
built-in tools via `--tools ""`) for both public profiles; the two light
system prompts differ and are both ≤600 chars and claim no capability;
`_resolve_model_profile("light")` is `None`; HTTP `model: "light"` still
400s.

## Issues / Blockers

None. Deploy is explicitly out of scope for this task (see Deploy above).

## Notes for Reviewer

- I added a rule (`[C-LEVEL DIGEST]` → `order_for_cto`) beyond the brief's
  literal ask, to close a gap where the automated digest turn could get
  shortcut into the light lane by a confident `chitchat` verdict — see
  "Rules added" item 1 for the reasoning. Flagging for explicit sign-off
  since it's outside the brief's D3 example list, though it touches only
  the declared `config/decisions/sompong.route.yaml` file.
- `_decision_is_confident` is duplicated locally in `secretary_server.py`
  rather than imported from `tools/flow_shoot.py`, matching the existing
  convention (see `tests/test_decide_browser_sites.py`'s comment: importing
  `flow_shoot` would pull in browser/playwright-adjacent code, and
  `tools/decide.py` itself is out of every consumer's declared touch
  surface). A parity test (`test_decision_is_confident_matches_flow_shoot_gate`)
  keeps the two copies honest.

## Skill learning
- (none)
