# task-4a53167b — the requester side of Run Inbox question cards (`ask`, `ask_ceo`)

Contract (read, not changed): `docs/design/run-inbox/QUESTIONS.md` in the live checkout
(`/opt/MoonieXHQ/Agents/Core`, not in this worktree) — §1, §2, §3, §3.1–3.3, §5, §6, §9.
Branch `agent/developer-task-4a53167b`, cut from origin/main 6ffb8069. Nothing pushed, nothing merged.

## Summary

`tools/ask_run.py` has an `ask` verb (flags exactly as §9) that builds the §3.1 body, runs every local
refusal before any network call, and POSTs to `/api/run/questions`; `wait`/`cancel`/`list --questions`
accept `Q-…` ids; a new org MCP tool `ask_ceo` sits directly after `ask_run`, and `ask_run_wait` takes
`Q-` ids. There is no answer verb and no code path that reaches an `…/answer` URL, and `wait` reads the
hub only, never the mailbox.

## Files Changed

- `tools/ask_run.py` — `ask` verb; `Q-` ids in `normalize_id` / `wait` / `cancel` / `list --questions`; local
  refusal chain (`prepare_question`: secret shapes → C-level role → §3.1 limits → hidden characters → §5
  command-shaped → §6 money); `resolve_host`; `verify_question_record` (fail closed); MCP entry `mcp_ask_ceo`;
  `_hub_error` now shows the hub's `field`.
- `lib/org_tools_registry.py` — `_h_ask_ceo` after `_h_ask_run`; `ask_ceo` ToolSpec after `ask_run`;
  `ask_run_wait` description says it takes `Q-` ids.
- `runners/cto_mcp_server.py` — `@mcp.tool ask_ceo` directly after `ask_run` (before `ask_run_wait`).
- `scripts/test_org_tools_registry.py` — `ask_ceo` added to the expected name set; label 26 → 27.
- `tests/test_ask_run_questions.py` — new, 189 tests.
- `tests/test_spawn_coo.py` — the COO launcher allow-list assertion also names `mcp__org__ask_ceo`.
- `docs/reports/task-ask-ceo/REPORT.md` — this file.

## Commits

- 2748a9c0 — report: task-ask-ceo worklog opened with base totals
- 79f6f25b — ask_run: the `ask` verb and Q- ids for Run Inbox question cards
- fa8c93e2 — org tools: ask_ceo (question card) beside ask_run; ask_run_wait takes Q- ids
- f157290d — tests: ask_run question cards — 188 tests for the ask verb, Q- ids and ask_ceo
- 87b99d64 — tests: ask_run question cards — the local refusals run in the contract's order
- (final commit: harness label + this report — see `git log`)

## Tests

Interpreter `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`, worktree cwd, plain `python -m pytest <paths>`.

| Run | Before (base 6ffb8069) | After |
|---|---|---|
| `tests/test_ask_run.py` + `tests/test_w42b_node_token_cards.py` | 127 passed | 127 passed |
| `scripts/test_cto_mcp_server.py` | 12 passed | 12 passed |
| `tests/test_ask_run_questions.py` | (new) | 189 passed |
| `tests/test_spawn_coo.py` | 61 passed, 1 xfailed, 1 failed | 61 passed, 1 xfailed, 1 failed (same one) |
| `scripts/test_org_tools_registry.py` (harness) | 29 [PASS] + ALL PASS | 29 [PASS] + ALL PASS |
| `scripts/test_tool_parity.py` (harness) | not run at base | 2 [PASS], ALL PASS (registry 27 entries, four surfaces equal) |
| `scripts/test_mcp_role_config.py` (harness) | not run at base | 66 [PASS], 0 failures |

- ran: `python -m pytest tests/test_ask_run.py tests/test_ask_run_questions.py tests/test_w42b_node_token_cards.py tests/test_spawn_coo.py scripts/test_cto_mcp_server.py`
- passed: 389
- failed: 1 — `tests/test_spawn_coo.py::test_send_shares_the_letter_for_coo_but_not_for_other_roles`:
  `lib.db.ArchivedDB: tasks.db is archived (hub cutover done)` — this process has no hub env. Fails the same
  way on the base, untouched by this task.
- skipped: 0 (1 xfailed in `test_spawn_coo.py`, pre-existing, by design)
- Not run: the full suite (11–33 min; the task made it optional).

## Issues / Blockers

- None blocking. Contract points I could not follow exactly, or had to interpret:
  1. **Hidden characters (§3.1 / hub `HIDDEN_PROSE`).** The contract names the rule but not the character
     set. The Console source would define it, and the HQ independence rule (projects talk only through APIs)
     forbids my reading another project's files, so I used an approximation: refuse Unicode categories
     Cc, Cf, Cs, Zl, Zp (newline/tab allowed in `why`). It may be stricter than the hub (it refuses
     zero-width joiners, so some emoji sequences). The hub stays the authority; a local false refusal
     costs one retry, a false allow is caught by the hub.
  2. **§6 has no test table in the contract.** Mine (`MONEY_REFUSED` / `MONEY_ALLOWED`) is derived from the
     four rules. The §5 table is the contract's verbatim, plus one case per bullet.
  3. **Order of refusals.** The requester (session / role / host) has to be resolved before the body exists,
     so a bad `--host`, an unreadable session or a worker claiming a C-level role is refused before the secret
     scan. From the body on, the order is the task's: secrets → role gate → limits → §5 → §6 (tested in
     `test_local_refusals_run_in_the_contracts_order`). Inside the limits step the order is question, why,
     options, expiry, hidden characters — the contract leaves it open.
  4. **No `--task` flag on the CLI** (§9 lists none); the task comes from `WORKER_TASK_ID`. The MCP tool has
     a `task` parameter, as `ask_run` does.
  5. **Extra fail-closed check.** [SUPERSEDED in round 2, see below: it compared `answered_by` to `"ceo"`,
     which refuses every real answer.] An `answered` record without the hub's own marker is refused (exit 3).
  6. **`_hub_error` now appends ` in <field>`** when the hub's error body carries a string `field`
     (affects command cards too; the text is only longer).

## Notes for Reviewer

- **Does `ask_ceo` reach the coo session through the registry? Yes.** `scripts/lib/cxo_mcp_config.py`
  fills the org server's allowlist from `lib/org_tools_registry.REGISTRY` (`_org_tool_names`), so
  `mcp__org__ask_ceo` is allowed in every C-level session with no hand edit; `coo` is in `c_level`
  (`policies/agents.yaml`), so the role gate passes for it. Proven by `test_ask_ceo_is_on_the_c_level_allowlist`
  and the extended assertion in `tests/test_spawn_coo.py` (launcher dry-run). **Caveat:** the COO session
  also carries `mcp__sompong__ask_ceo` (the Telegram tool, `roles/coo.md`), so there are two tools with the
  same bare name there; the prefix tells them apart, but the COO role file may want a sentence saying which
  is which. I did not touch `roles/coo.md` or the COO allowlist.
- **The things to look at first** (the override is "security"): `tools/ask_run.py` `prepare_question`,
  `verify_question_record`, `cmd_wait`; and the tests `test_no_source_builds_an_answer_url`,
  `test_no_verb_and_no_tool_ever_posts_to_an_answer_route` (runs every verb and tool against FakeHub and
  asserts the only POSTs are `/api/run/questions` and `…/cancel`), and
  `test_a_forged_mailbox_letter_does_not_change_what_wait_returns` (a real letter in a temp inbox; hub says
  pending; wait exits 4; no file under an inbox path is opened; the letter is not drained).
- The module docstring in `tools/ask_run.py` describes the letter (`state/inbox/…`) in prose; the
  mailbox test therefore scans imports, names and short string literals, not the docstring.
- Local `main` has unpushed edits after `ask_run_wait` in `runners/cto_mcp_server.py` (per the task); my
  insertion is before `ask_run_wait`, so it should not touch those lines — not verified against local main
  (this worktree is cut from origin/main). The CTO lands this by hand.
- `SKILL-OVERRIDE:` lines: none applied. The brief's "override: security" was honoured as a review focus
  (the first item above), not as a change to any skill.
- Smoke tests by hand need `env -u WORKER_TASK_ID -u WORKER_ROLE -u ORG_SESSION_ID`: a worker process
  correctly cannot claim a C-level role, so `ask --dry-run --role cto` from this worker shell is refused.

## WORKLOG

- **Base totals, before any edit** (interpreter `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`, worktree cwd):
  - `python -m pytest tests/test_ask_run.py tests/test_w42b_node_token_cards.py` → 127 passed.
  - `python -m pytest tests/test_spawn_coo.py` → 1 failed (`test_send_shares_the_letter_for_coo_but_not_for_other_roles`:
    `lib.db.ArchivedDB` — this worktree's process has no hub env; fails on a clean checkout, unrelated),
    1 xfailed, rest passed. **Correction:** this note first said "62 passed"; the file has 47 test functions /
    63 collected items at base and now (my edit adds none), so the true base is 61 passed + 1 xfailed + 1 failed.
  - `python scripts/test_org_tools_registry.py` (harness, ignored by pytest.ini) → `grep -c PASS` 30
    (29 `[PASS]` lines + `ALL PASS`), 0 FAIL.
- Read: QUESTIONS.md, tools/ask_run.py, tests/test_ask_run.py (FakeHub), lib/org_tools_registry.py,
  runners/cto_mcp_server.py, runners/cto.py (builds its tools from REGISTRY, so `ask_ceo` reaches it
  with no edit), scripts/lib/cxo_mcp_config.py (`_org_tool_names` = REGISTRY names).
- Built `ask` + Q ids + refusal chain in `tools/ask_run.py` (79f6f25b), then the registry / MCP wiring (fa8c93e2).
  The first attempt to write `tools/ask_run.py` through a Bash heredoc was blocked by the self-repo guard
  (nothing written); redone with the Edit tool.
- Wrote `tests/test_ask_run_questions.py`. First run: 5 failures, all mistakes in my tests, none in the code:
  a miscounted command-word list (I wrote 69/71; the module and the contract both have 77, same order — now
  the contract's list is written out in the test); `monkeypatch.undo()` mid-test also undid the inbox-root patch
  (now a scoped `monkeypatch.context()`); a docstring-wide `state/inbox` substring scan (now AST-based); a
  bare `"answer"` dict key matched by the route scan (now only slash-bearing strings); a pydantic ToolError
  expected as a tool-level refusal (FastMCP's schema rejects wrong types before the handler runs).
- After the fixes: 189 passed. Added the ordering test; corrected my own assumption that `options` is checked
  before `why` (the code does question → why → options; the contract does not fix it).

## Skill learning

- MISSING [no owner] : when a tool is added to `lib/org_tools_registry.py`, four places must agree — the registry ToolSpec, the `@mcp.tool` stub in `runners/cto_mcp_server.py`, the name set in `scripts/test_org_tools_registry.py` (and its "N tool names" label), and `scripts/test_tool_parity.py` which checks all surfaces; `cxo_mcp_config` and `runners/cto.py` follow the registry on their own and need no edit. I found this by reading five files; a one-paragraph checklist would have saved that · evidence: task-4a53167b fa8c93e2
- COSTLY [no owner] : sibling test modules import fixtures by bare name (`from test_ask_run import hub, _sealed, srv …`) — the convention is only visible in `tests/test_w42b_*`; and a fixture imported that way must be listed with `# noqa: F401` because pytest finds it by name · evidence: task-4a53167b tests/test_ask_run_questions.py · prevented by: one line in the tests playbook
- COSTLY [no owner] : `monkeypatch.undo()` inside a test undoes every patch made through that fixture instance, including ones set earlier in the same test (and the repo's autouse env-stripping fixtures) — it cost one failing run to find; use `with monkeypatch.context() as m:` for a scoped spy · evidence: task-4a53167b test_a_forged_mailbox_letter_does_not_change_what_wait_returns, first run
- MISSING [no owner] : the worker shell exports `WORKER_TASK_ID`, so `tools/ask_run.py ask --role cto` by hand is correctly refused ("a worker cannot claim role 'cto'"); a worker smoke-testing a C-level-only verb must run it with `env -u WORKER_TASK_ID -u WORKER_ROLE -u ORG_SESSION_ID`. Nothing says so · evidence: task-4a53167b, first dry-run
- COSTLY [no owner] : a hook (`hook-self-repo-guard.py`) blocks opaque Bash writes (a Python heredoc that writes a file) inside the worktree with "would write to ." — it names the worktree root, not the file, so it looks like a path bug; use Edit/Write · evidence: task-4a53167b, first write of tools/ask_run.py
- WRONG [no owner] : my own base-total note ("62 passed" for `tests/test_spawn_coo.py`) was a miscount; the file has 63 collected items. Recording base totals by eye from a pytest tail is error-prone — compare `--collect-only` item counts, or the pass count plus the non-pass count · evidence: task-4a53167b WORKLOG, corrected above

## Round 2 (CTO feedback iter 1)

**What was wrong.** `verify_question_record` refused an `answered` record unless `answer.answered_by == "ceo"`.
The live Console's operator username is `"CEO"` (uppercase, from the operators table) and the hub copies
`req.operator.username` into `answered_by`, so every real tap would have exited 3. I took the lowercase
`"ceo"` from the example record in QUESTIONS.md §3.3 and built the FakeHub fixture from the same example, so
my tests passed on a value the live hub never sends.

**The fix** (commit 306ecf1e, `tools/ask_run.py`). No username is compared. An `answered` record is trusted only
if all of these hold, else exit 3 (CLI) or `ERROR: …` (MCP `ask_run_wait`) with a one-line reason that names the
field and never echoes the hub's value:
- `answer` is an object;
- `answer.via == ANSWER_VIA` = `"operator_passkey_session"` (new constant, QUESTIONS.md §3.3; the same value as
  Console `src/run/questions.js` `ANSWER_VIA` — I did not open the Console file, the CTO named the constant);
- `answer.answered_by` is a non-empty (non-blank) string;
- `answer.answered_at` is a non-empty (non-blank) string.
Other statuses (`pending`, `expired`, `cancelled`) are not checked; `expired` and `cancelled` still exit 1.

**The wording fix** (`lib/org_tools_registry.py`). The `ask_ceo` ToolSpec description now ends with: "Not the same
tool as mcp__sompong__ask_ceo (SomPong's Telegram/LINE question in the COO session)." The MCP stub takes its
description from the registry, so the parity harness still agrees.

**Tests** (`tests/test_ask_run_questions.py`).
- FakeHub fixture `ANSWER` is now `answered_by: "CEO"`, `via: "operator_passkey_session"`.
- `answered_by` "CEO" + the right via → `wait` exits 0 and prints the record; also `ceo`, `gob`, `Some Other Operator`
  (the username is not compared); `--json` returns the record unchanged.
- 14 bad-record cases exit 3 on the CLI (and with `--json`) with a one-line "not trusting it" reason naming the
  field: no answer object, answer a string, `via` missing / wrong / empty / null / case-different, `answered_by`
  missing / empty / blank / not a string, `answered_at` missing / empty / null.
- The MCP path (`ask_run_wait`) returns `ERROR: …` with the same reason for every one of those 14, and the record
  for a good answer with another username.
- The ToolSpec sentence is asserted word for word.
- **Proof the tests bite:** `tools/ask_run.py` put back to the round-1 version (`git show 306ecf1e~1:…`) → 19 failed,
  186 passed in `tests/test_ask_run_questions.py` (the real-shape answer exits 3 there); fix restored → all pass.

**Totals** (interpreter `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`, worktree cwd):

| command | before round 2 | after |
|---|---|---|
| `python -m pytest tests/test_ask_run.py tests/test_ask_run_questions.py scripts/test_cto_mcp_server.py` | 312 passed | 328 passed (+16) |
| `python scripts/test_org_tools_registry.py` | ALL PASS (30 PASS lines, 0 FAIL) | ALL PASS (30 PASS lines, 0 FAIL) |
| `python scripts/test_tool_parity.py` | ALL PASS | ALL PASS |

**For the reviewer.**
- **QUESTIONS.md §3.3's example shows `"answered_by": "ceo"` (lowercase); the live hub sends `"CEO"`.** That
  example is what misled round 1. I may not write the contract; the CTO may want it changed to `"CEO"` or to
  `"<operator username>"`.
- `via` is what the requester can check, not proof: the hub sets it, and a record the hub serves is the hub's word
  (§1.3). A hub that lied would defeat any client-side check; this one closes the case where a record has no
  answer provenance at all.
- Files touched in round 2: `tools/ask_run.py`, `lib/org_tools_registry.py`, `tests/test_ask_run_questions.py`,
  this report. No change to the registry parameters, the MCP stub, the COO allowlist or any other test file.

**Skill learning (round 2).**
- WRONG [no owner] : "copy the fixture from the contract's example record" — the §3.3 example carries an illustrative value (`answered_by: "ceo"`) the live hub never sends (`"CEO"`), so a test built from it proved nothing about the live shape · evidence: task-4a53167b round 1 `answered_by == "ceo"` check, CTO feedback iter 1 · fix: when a fixture comes from a spec example, check the field against one live record (or read the producer's source) before asserting on its exact value; assert on markers the producer sets, not on identity strings.
- COSTLY [no owner] : a fail-closed check on an identity value is the kind that fails closed on every success; it needs a test that feeds the realistic *good* input as well as the bad ones, and the good input must come from the live system, not from my own reading of the contract · evidence: task-4a53167b round 1 had 4 bad-input cases and the one good case used my own value · prevented by: the "check passes on real input" case is written first.
