# REPORT — task-b8a9a714: browser_operator page-state decisions via `decide()`

## Summary

Wired `tools/decide.py`'s typed decision layer (landed by T1, task-2a29d27e)
into both browser-driving runners — `tools/flow_shoot.py` (Google Flow) and
`scripts/higgsfield/gen_loop.py` (Higgsfield) — so a poll loop asks a typed
question ("what state is this page in?") instead of scanning full page text
or a screenshot. Added a small-state extractor per surface, wired the
decision into each runner's poll loop with a conservative action-mapping
gate (act only on `provider=="rules"` or `probs[choice]>=0.9`; everything
else stops the run rather than guessing), extended both `browser.*` decision
sites' rules with measured strings, granted `mcp__org__decide` to all
workers, and drafted (but did not apply) the `browser-operator` skill
section for the CTO to fold in.

## Files Changed

- `config/decisions/browser.page_state.yaml` — added an `idle` rule
  (Higgsfield's bare-`Generate`/struck-price button text); extended
  `moderated` (nsfw, "confirm rights"), `rate_limited` (Higgsfield's "1
  unlimited generation at a time" toast), `generating` (processing/in
  progress), and `error` (bare "Failed", "prompt is required") with measured
  strings from both skills and from `gen_loop.py`'s own pre-existing ad hoc
  regex. No new options added.
- `config/decisions/browser.moderation_action.yaml` — extended
  `escalate_ceo`'s pattern with "confirm rights" (Higgsfield's Confirm
  Rights button label, alongside the existing "rights verification
  required" banner text). No new options added.
- `tools/flow_shoot.py` — added `EXTRACT_STATE_JS` + `extract_state(page)`
  (with a verification table), `_decision_is_confident()`, and
  `_poll_hazard_or_none()`; rewrote `FlowBrowser.poll_result()` to call
  `decide("browser.page_state", ...)` / `decide("browser.moderation_action",
  ...)` instead of the old full-body `is_refusal_text()` scan; updated
  `cmd_run()` to stop the whole run on a confident `signed_out`/`error`
  read and to exit non-zero on `escalate_ceo`, never re-firing on either.
  `is_refusal_text()` is unchanged (kept as a thin wrapper — its two
  patterns now also live as yaml rules).
- `scripts/higgsfield/gen_loop.py` — moved the top-level `playwright` import
  into `main()` (matches `flow_shoot.py`'s lazy-import convention, and is
  what makes this module importable in tests without Playwright installed);
  added `EXTRACT_STATE_JS` + `extract_state(page)`, `_decision_is_confident()`
  (duplicated, not imported — see Skill learning), `_ts_from_url()` /
  `_hf_urls()` (extracted from `main()`'s inline closures), and
  `poll_for_result()` (the new, testable completion-poll loop); `main()` now
  calls `poll_for_result()` and handles `stopped`/`escalate_ceo`/`refusal`
  the same way `flow_shoot.cmd_run()` does.
- `runners/worker_init.py` — added `mcp__org__decide` to `_BASE_WORKER_TOOLS`
  (every worker, not just `browser_operator` — Deliverable 3 did not scope
  it narrower, and `decide()` is useful outside browser surfaces too, e.g.
  `skill.route`/`sompong.route`).
- `tests/test_decide_browser_sites.py` (new) — rules-mapping coverage for
  both sites against measured strings, plus the action-mapping gate.
- `tests/test_flow_shoot.py` (extended) — `poll_result()` against a fake
  page for every state (moderated+escalate, moderated+rewrite_dialogue,
  signed_out, error, generating/unknown-keep-polling, download-wins-mid-poll),
  plus `cmd_run()` hazard-handling (stopped halts the whole run,
  escalate_ceo exits, never re-fires) and money-guard tests proving
  `decide()` is never called under `--dry-run` or `--credit-cap 0`.
- `tests/test_higgsfield_gen_loop.py` (new) — same shape for
  `poll_for_result()`/`extract_state()`, plus a byte-for-byte parity check
  against `flow_shoot._decision_is_confident`.
- `REPORT.md` (this file).

## Call chains

**Flow** (`tools/flow_shoot.py`):
`cmd_run()` (CLI `run` subcommand)
→ `_submit_or_raise()` → `browser.submit()` (spends credits)
→ `browser.poll_result()` — each cycle:
  → `extract_state(page)` (one `page.evaluate(EXTRACT_STATE_JS)` call)
  → `decide_tool.decide("browser.page_state", state_text)`
  → if `_decision_is_confident(decision)` and `choice == "moderated"`:
    → `decide_tool.decide("browser.moderation_action", state_text)`
    → returns `{"status": "refusal", "moderation_choice": ...}`
  → if confident `signed_out`/`error`: returns `{"status": "stopped", "reason": ...}`
  → else (idle/generating/rate_limited/unknown/low-confidence): keep polling
→ back in `cmd_run()`: `_poll_hazard_or_none(result)` →
  `escalate_ceo` → `sys.exit(...)` (never re-fires) ·
  `stopped` → mark row failed, log, `break` (halts the whole run) ·
  `refusal` (non-hazard) → existing re-fire-once-then-mark-refused path,
  unchanged.

**Higgsfield** (`scripts/higgsfield/gen_loop.py`):
`main()` (loop over the CSV's todo rows)
→ `page.locator('button[type=submit]').first.click()` (spends nothing extra —
  Unlimited-gated by `ensure_config()` earlier in the loop, unchanged)
→ `poll_for_result(page, t0_max)` — each cycle:
  → `_hf_urls(page)` / `_ts_from_url()` (the real completion signal, checked
    first and unchanged from the original inline loop)
  → `extract_state(page)` (one `page.evaluate(EXTRACT_STATE_JS)` call)
  → `decide_tool.decide("browser.page_state", state_text)`
  → same moderated/signed_out/error/else branching as Flow above, calling
    `decide_tool.decide("browser.moderation_action", ...)` on `moderated`
→ back in `main()`: `stopped` → log, `break` (halts the whole run) ·
  `moderation_choice == "escalate_ceo"` → `sys.exit(...)` ·
  `refusal` (non-escalate) → log refused, `continue` to next clip ·
  `download` → existing download/upload/index path, unchanged.

Gate 4b check: both hazard branches are exercised by `cmd_run()`/`main()`
integration tests using stub browsers whose `poll_result()`/`poll_for_result()`
return the hazard directly (`test_stopped_page_state_halts_the_whole_run_not_
just_this_shot`, `test_escalate_ceo_exits_the_runner_and_never_re_fires` in
`tests/test_flow_shoot.py`) — the guard is exercised through the real
call chain, not only unit-tested in isolation.

## Selector / marker verification table

| surface | marker | verified | source |
|---|---|---|---|
| Flow | `button[aria-label="เริ่มสร้าง"]` | 2026-09-19 (task-04851451) | same selector `FlowBrowser.submit()` already clicks live |
| Flow | `ล้มเหลว` / `อาจละเมิดนโยบาย` body substrings | 2026-09-19 (`is_refusal_text`) | refusal card text, moved into `browser.page_state.yaml` |
| Flow | `sign in` / `accounts.google.com/ServiceLogin` | **unverified 2026-09-22** | google-flow-ops SKILL.md §"Mid-session Google sign-out" — no live browser session available this task |
| Flow | `429` / rate limit / slot-busy | **unverified 2026-09-22** | memory: `reference_rate_limited_false_positive_from_higgsfield_429.md` |
| Flow | generating / in queue / queued / rendering | **unverified 2026-09-22** | heuristic wording, no confirmed Flow UI string |
| Flow | download / ready to download / generation complete | **unverified 2026-09-22** | heuristic; the real completion signal stays the captured CDN URL (`CDN_VIDEO_RE`), checked first, unchanged |
| Higgsfield | `button[type=submit]` | 2026-09-19 (this file's own `ensure_config`/`main`, pre-existing) | the Generate/Unlimited button |
| Higgsfield | `.hfnav-auth-login` | 2026-09-19 (this file's own `main()` `NOT_LOGGED_IN` check, pre-existing) | signed-out indicator |
| Higgsfield | "Rights verification required" / "Confirm Rights" | **unverified 2026-09-22** | higgsfield-unlimited-gen SKILL.md § HARD rule 3 |
| Higgsfield | "1 unlimited generation at a time" | **unverified 2026-09-22** | higgsfield-unlimited-gen SKILL.md § HARD rule 4 |
| Higgsfield | "NSFW" | **unverified 2026-09-22** | higgsfield-unlimited-gen SKILL.md stop-and-ask checklist |
| Higgsfield | "Prompt is required" | **unverified 2026-09-22** | higgsfield-unlimited-gen SKILL.md, measured composer error text |
| Higgsfield | bare "Failed" card text | **unverified 2026-09-22** | carried over from this file's own pre-existing, previously-unused `failed_count()` heuristic |
| Higgsfield | generating/processing/queued/rendering/in progress | 2026-09-19 (this file's own pre-existing ad hoc regex, moved here) | |

No browser session was available in this worker, so every selector not
already load-bearing in the pre-existing code is marked `unverified
2026-09-22`, per the task's explicit fallback instruction — the current
heuristic (full-body regex scan, now moved server-side into the small JS
snippet so only the matched excerpt is returned) stays behind each one.

## Drafted skill section (Deliverable 5 — DRAFT ONLY, not applied to the skill file)

Proposed addition to `.claude/skills/browser-operator/SKILL.md` (owner: CTO,
ADR 0026 — this worker did not edit that file):

> ## A typed question about the page is answered by `decide`, never by a screenshot
>
> **HARD.** Before asking "is it still generating?", "is that card a
> refusal?", or "am I signed out?" on Google Flow or Higgsfield, extract the
> smallest sufficient page text with `javascript_tool` and call
> `mcp__org__decide`. Never re-derive the answer from a fresh screenshot or a
> full `innerText` dump.
>
> **Why hard:** a wrong guess here can re-fire a paid generation (a refusal
> is refunded; a wrongly re-submitted generation is not) — ADR 0022 §7's
> first HARD test ("does breaking this rule spend money or consume a
> paid/limited resource") is met directly.
>
> **The snippet** (same shape `tools/flow_shoot.extract_state()` /
> `scripts/higgsfield/gen_loop.extract_state()` use — adapt the button
> selector per site):
>
> ```js
> () => {
>   const clip = (s, n) => (s || '').replace(/\s+/g, ' ').trim().slice(0, n);
>   const body = document.body.innerText || '';
>   const parts = [];
>   const btn = document.querySelector('button[type=submit]'); // Higgsfield
>   // const btn = document.querySelector('button[aria-label="เริ่มสร้าง"]'); // Flow
>   if (btn) parts.push('button="' + clip(btn.innerText, 60) + '" disabled=' + !!btn.disabled);
>   const markers = [
>     /(rights verification required|confirm rights)[^\n]{0,80}/i,
>     /(sign in|accounts\.google\.com\/ServiceLogin)[^\n]{0,80}/i,
>     /(429|too many requests|rate limit|slot.?busy|1 unlimited generation at a time)[^\n]{0,80}/i,
>     /(generating|processing|queued|rendering|in progress)[^\n]{0,40}/i,
>     /(something went wrong|failed to generate|\bfailed\b|prompt is required)[^\n]{0,80}/i,
>     /ล้มเหลว[^\n]*\n?[^\n]*/,
>   ];
>   for (const re of markers) { const m = body.match(re); if (m) parts.push(clip(m[0], 200)); }
>   return parts.join(' | ').slice(0, 1500);
> }
> ```
>
> Then: `mcp__org__decide(site="browser.page_state", state=<the returned text>)`.
>
> | outcome | what to do |
> |---|---|
> | `idle` / `generating` / `rate_limited` / `done` (any confident, or no confident match) | keep waiting — none of these are a hazard; do not stop or escalate on a guess |
> | `moderated`, confident | call `mcp__org__decide(site="browser.moderation_action", state=<same card/toast text>)` |
> | → `escalate_ceo` | **stop. File a blocker. Never re-fire.** Human call only (Face/IP resemblance, rights verification). |
> | → anything else confident (`retry_same`/`rewrite_dialogue`/`rewrite_chips`/`skip`) | act on it; a refusal is refunded so a single re-fire is safe |
> | `signed_out` / `error`, confident | **stop.** File a blocker with the extracted state text. Do not sign in, do not retry blind. |
> | any decision where `provider != "rules"` and `probs[choice] < 0.9` | treat exactly like "no confident match" — never act on a guess, whatever the site |

## Tests

- ran: `python3 -m pytest scripts/ tests/ --import-mode=importlib -p no:warnings --ignore=scripts/test_skill_doctrine_lint.py -q` (via the org `.venv`, which is where Playwright/yaml/requests are actually installed — the bare `python3`/`pip` on this Mac has none of them)
- passed: **1467** (main was 1427 — net **+40** new, 0 removed/broken)
- failed: **0**
- skipped: **18** (main was 15; all 3 extra skips are pre-existing environment gates — `ORG_TEST_DB_URL`/local-`.venv` skips in `tests/test_db_backend_pg.py` and `scripts/test_session_remote_control.py`, unrelated to this task's files — confirmed via `-rs` skip-reason listing, none reference `decide`/`flow_shoot`/`gen_loop`)
- new test files individually: `tests/test_decide_browser_sites.py` (20 passed), `tests/test_higgsfield_gen_loop.py` (12 passed); `tests/test_flow_shoot.py` grew from 63 to 76 passed (13 new)
- `python tools/decide.py report` after a real (non-tmp-redirected) call to each site shows both `browser.page_state` and `browser.moderation_action` rows (verified live in this session — not reproduced here since it's gitignored runtime state)
- `python -c "from runners import worker_init as w; assert 'mcp__org__decide' in w._BASE_WORKER_TOOLS"` — passes

## Issues / Blockers

- None blocking. The only real limitation is the "unverified" selectors
  table above — this worker had no live browser session (Chrome MCP tools
  were not exercised; this is a pure code task). The next browser_operator
  run against Flow/Higgsfield should confirm or correct those markers and
  update the table's dates.
- Found and corrected a likely typo in the task brief: the Tests section
  says "copyright text → rewrite_dialogue", but the already-landed
  `config/decisions/browser.moderation_action.yaml` (T1, task-2a29d27e) maps
  copyright/IP/trademark to `rewrite_chips`, whose own `meaning` states
  explicitly "rewrite the Element/chip, NOT the dialogue" — the opposite of
  what the brief's example implies. Followed the correct, semantically
  accurate mapping (`rewrite_chips`) rather than the brief's literal
  wording; documented and tested as `test_copyright_text_is_rewrite_chips_
  not_rewrite_dialogue` in `tests/test_decide_browser_sites.py`.

## Notes for Reviewer

- `_decision_is_confident()` is duplicated verbatim in `tools/flow_shoot.py`
  and `scripts/higgsfield/gen_loop.py` rather than added to
  `tools/decide.py`, because that file is outside this task's declared
  touch surface. If a third browser-driving runner needs this logic, it's
  worth promoting to `tools/decide.py` as a real utility at that point
  (flagged below under Skill learning as well).
- `browser.page_state.yaml`'s new `idle` rule only matches
  `extract_state()`'s own `button="..." disabled=...` framing (never raw
  page prose), so it can't accidentally fire on unrelated text containing
  the word "generate".
- `scripts/higgsfield/gen_loop.py`'s `playwright` import move (module-level
  → inside `main()`) is a behavior-neutral refactor required to make the
  module importable/testable at all (the org `.venv` has Playwright, but
  the module-level import made it impossible to unit-test `extract_state`/
  `poll_for_result` without a live browser) — verified via `py_compile` and
  the new test file's clean import.

## Skill learning

- MISSING [browser-operator §"A typed question about the page is answered by decide"] : the skill has no section at all telling an operator to call `decide` instead of a screenshot for a typed page-state question — this is Deliverable 5's drafted section above, for the CTO to fold in · evidence: task-b8a9a714, `.claude/skills/browser-operator/SKILL.md` (unedited by this worker, per ADR 0026)
- MISSING [google-flow-ops / higgsfield-unlimited-gen — no shared "verified selector" ledger] : both skills document measured strings in prose scattered across a 1700+ line file each; a dedicated, dated selector table (like the one in this report) would make Deliverable-1-style "mark unverified with a date" work faster for the next task that needs it · evidence: task-b8a9a714, this report's selector table took a full read-through of both SKILL.md files to assemble
- WRONG [task brief §Tests] : "copyright text → rewrite_dialogue" does not match the landed `config/decisions/browser.moderation_action.yaml`'s own `rewrite_chips` mapping (whose `meaning` explicitly says NOT the dialogue) · evidence: task-b8a9a714, `config/decisions/browser.moderation_action.yaml`, `tests/test_decide_browser_sites.py::test_copyright_text_is_rewrite_chips_not_rewrite_dialogue` · fix: when a future task brief's worked example conflicts with an already-landed, reviewed config file, treat the config as authoritative and flag the brief text rather than editing the config to match a probable typo
- COSTLY [no owner] : the exact integration point for gen_loop.py's decide() call took real time to resolve — the task brief cites "lines ~161–183, the GENERATE button / data-state logic" for the Unlimited-mode config-toggle block, which doesn't share browser.page_state's schema (idle/generating/moderated/...) at all; the actual analogous "poll for result" loop is ~80 lines further down (~337–359 in the pre-edit file) and had zero moderation/error detection previously · evidence: task-b8a9a714, `scripts/higgsfield/gen_loop.py` diff · prevented by: a task brief citing line numbers for an integration point should also name the target function, not just a line range, since scripts drift and a line range alone can point at the wrong logical block
