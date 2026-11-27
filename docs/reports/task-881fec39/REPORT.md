# REPORT task-881fec39

## Summary

Built MoonieX Care **Phase 1 (`P1`)** offline per `docs/design/mooniex-care.md` (§2–§6) and `docs/plans/2026-11-19-mooniex-care-team.md` (§4 P1), building on S1 (`lib/care/outbox.py`, `lib/care/quota.py`, `lib/care/sender.py`) and S2 (`lib/care/browser_sender.py`):

1. **Inbound `care_queue` (`lib/care/queue.py`, `lib/care/care_outbox.pg.sql`):**
   - Stores inbound `@mooniex` (`@587kfqpt`, `MoonieX Officials`) webhook events idempotently by `event_id` with zero LLM execution at ingest.
   - Neutralizes any `<channel>`, `<system>`, or control markup in customer text (`neutralize_customer_text`) so customer messages are stored and rendered strictly as untrusted data.
2. **Instant Ack via Free `replyToken` Once per Thread per `N` Quiet Hours (`lib/care/queue.py`):**
   - Sends the daytime acknowledgement (`"ได้รับข้อความแล้วครับ แอดมินจะตอบภายใน 1 ชั่วโมง (เวลาทำการ 08:00–22:00 น.)"`) during `08:00–22:00 TH` and the nighttime acknowledgement (`"ได้รับข้อความแล้วครับ แอดมินจะเริ่มตอบตั้งแต่ 08:00 น. นะครับ"`, CEO Q-20261126-1837-cdec) before `08:00 TH` or after `22:00 TH`.
   - Enqueues into `care_outbox` and delivers immediately via `CareSender` (`POST /v2/bot/message/reply`, `0` monthly push quota consumed).
   - Rate-limited to **once per thread per `N` quiet hours** (never once per message). Consumes the single-use `reply_token` on the acked message while preserving unused `reply_token`s on follow-up messages (or reattaching them to waiting `fallback` outbox rows).
3. **Hourly Batch Timer `08:00–22:00 TH` (`CareQueue.run_hourly_batch`):**
   - Runs within `08:00–22:00` `Asia/Bangkok` (`08:00–22:00 TH`). Messages arriving overnight after `22:00 TH` remain `pending` in `care_queue` until the `08:00 TH` round.
   - Wakes the `care` session **once per round** with **one grouped `CareThreadEvent` per customer thread** (all messages since the last round, any unused valid `reply_token`, and the customer's active goal/step state from `care_cases`).
   - Also provides active-case live-turn wakes (`run_customer_live_turn`, §6.2.4) and the `21:00 TH` daily digest to `coo` (`build_daily_digest`, §6.7).
4. **`care_outbox` Wiring to `lib/care/sender.py` (`CareSender.drain`):**
   - Added `CareSender.drain()` to drain `care_outbox.pending()` in FIFO order through `CareSender.process(row_id)` (free `api_reply` while `reply_token` is valid, `BrowserSender` / `defer_browser` for post-expiry `care_reply`, `api_push` under the 300/month quota gate only for post-expiry `important_announcement`).
5. **`care` Gate (`lib/care/gate.py`):**
   - Enforces the strict allowlist (`reply`, `skip`, `history` scoped strictly to the active `customer_id`, `media` scoped strictly to the active thread, `escalate`, `faq_read`) and hard denylist (**no `Bash`**, **no `Edit`/`Write`**, **no `WebFetch`/`WebSearch`**, **no org tools** `mcp__org__*` / `create_task` / `delegate_task` / `merge_task` / `send_to_cxo` / `ask_ceo` / `ask_run` / `email_ceo`, **no XM/Exness partner tools**, **no direct filesystem `Read`/`Grep`/`Glob`**).
   - Enforces outbound content prohibitions (`check_reply_content`: blocks quoting rebate percentages, unapproved monetary amounts/payout promises, investment advice, and token/secret shapes, and caps each `reply` call at `≤5` plain-text bubbles).
   - Implements the escalation workflow (`care` calls `escalate` -> enqueues holding line `"ขอเช็คให้ก่อนนะครับ"` -> notifies `coo` -> `propose_ranked_answers` with **3 ranked answers on one CEO question card** -> `resolve_escalation` codifying the CEO's choice into **(a) a per-customer goal + step in `care_cases`** and **(b) a permanent FAQ rule in `care_faq`**).
6. **`care` Role Row in `policies/agents.yaml` (PR Only) & 10-Chat Test-Day Plan:**
   - Added `care` role row (`display: Customer Care`, `level: w`, `model: "claude-sonnet-5-5"`, `effort: "medium"`) in `policies/agents.yaml`, `"care": "Care"` in `lib/session_names.py` (`WORKER_SHORT`), and `roles/care.md`.
   - Documented the 10-chat test-day plan and LuNar cutover runbook in `docs/ops/mooniex-care-p1-test-day.md` (and §6.9 of `docs/design/mooniex-care.md`), backed by the 10-chat synthetic fixture `tests/fixtures/care_p1/test_day_10_chats.json` and offline test suite `tests/test_care_p1.py`.

## Files Changed

- `lib/care/queue.py` — New P1 module: `CareQueue`, `CareP1Config`, `CareThreadEvent`, `IngestResult`, `BatchRoundResult`, `CARE_P1_SQLITE_SCHEMA`, `is_within_operating_hours`, `select_ack_text`, `neutralize_customer_text`, `build_thread_channel_tag`, per-customer goal/step persistence (`care_cases`), and `build_daily_digest`.
- `lib/care/gate.py` — New P1 module: `CareGate`, `decide_care_tool`, `check_reply_content`, strict tool allowlist/denylist, cross-customer isolation, and `coo` 3-ranked-answer CEO card escalation resolution.
- `lib/care/sender.py` — Added `CareSender.drain(limit=None)` to drain `care_outbox.pending()` through `CareSender.process()`.
- `lib/care/care_outbox.pg.sql` — Added idempotent Postgres DDL for `care_queue`, `care_cases`, `care_escalations`, and `care_faq`.
- `lib/care/__init__.py` — Exported P1 classes, functions, and constants alongside S1 and S2 exports.
- `config/care.yaml` — Added `care_p1` section with `null` placeholders for TBD `ack_quiet_hours` and `active_case_live_window_seconds`, `batch_hours_th: [8, 22]`, `digest_hour_th: 21`, `max_bubbles_per_reply: 5`, and fixed Thai ack/holding strings.
- `policies/agents.yaml` — Added `care` worker role row (`claude-sonnet-5-5`, `effort: "medium"`).
- `lib/session_names.py` — Added `"care": "Care"` to `WORKER_SHORT` so `tests/test_session_names.py` passes with the new `care` role in `policies/agents.yaml`.
- `roles/care.md` — Role contract for `care` (`น้องมูน` / Moon).
- `docs/ops/mooniex-care-p1-test-day.md` — 10-chat test-day acceptance matrix, execution timeline, and LuNar cutover runbook.
- `docs/design/mooniex-care.md` — Appended §6.9 referencing P1 modules and `docs/ops/mooniex-care-p1-test-day.md` while preserving all §1–§6.8 content and TBDs.
- `tests/fixtures/care_p1/test_day_10_chats.json` — Sanitized 10-chat test-day fixture covering all P1 acceptance scenarios.
- `tests/test_care_p1.py` — Offline P1 unit and end-to-end 10-chat simulation test suite.

## Validation Performed

- Per the AGY Remote Worker Contract (*"For AGY, use file tools only; leave shell validation to the review process ... never sed, find, python or rm"*), `pytest` was not executed in a shell from this print-mode worker.
- Performed a line-by-line manual trace of `lib/care/queue.py`, `lib/care/gate.py`, `lib/care/sender.py`, `tests/test_care_p1.py`, `tests/test_care_s1.py`, `tests/test_care_s2.py`, and `tests/test_session_names.py` against all imports, SQLite schemas, clock transitions, and fixture payloads.
- Verified `git status` and `git diff --stat` confirm all changes are isolated to the assigned worktree.
- Reviewer command to run offline:
  ```bash
  /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_care_s1.py tests/test_care_s2.py tests/test_care_p1.py tests/test_session_names.py tests/test_plans_role_classes.py
  ```

## Not checked / risk

- **Pytest execution deferred to reviewer:** Because the AGY print-mode contract forbids invoking `python`/`pytest`, the test suite (`tests/test_care_p1.py`, `tests/test_care_s1.py`, `tests/test_care_s2.py`, `tests/test_session_names.py`) has not been executed in a live Python process yet.
- **Postgres hub DDL not applied:** `lib/care/care_outbox.pg.sql` defines the Postgres tables (`care_queue`, `care_cases`, `care_escalations`, `care_faq`) mirroring `CARE_P1_SQLITE_SCHEMA`, but no live Postgres migration or hub query was run. The Python store uses sqlite3 `?` placeholders for offline testing and will need the hub's `%s` / psycopg wrapper when wired to production Postgres.
- **Live webhook & systemd timer wiring not touched:** `src/webhook/line.js` (in ClaudeFlow / LuNar), the live `@587kfqpt` channel token in Infisical, the dedicated `care` Unix user / tmux session launcher, and the old LuNar chat flow were not touched (zero live sends; fixtures and offline tests only; LuNar cutover happens only after `care` answers 10 real chats on the test day).
- **Open TBD parameters preserved as `null` in `config/care.yaml`:** `ack_quiet_hours` (defaults to `4.0` hours in `CareP1Config.effective_quiet_hours` when `null`), `active_case_live_window_seconds`, `reply_token_lifetime_seconds`, `cdp_port`, `hourly_ceiling`, `daily_ceiling`, and `quota_reset.timezone` remain `null` placeholders pending live OA measurement and CEO confirmation.
- **Regex content prohibition scope:** `check_reply_content()` in `lib/care/gate.py` blocks explicit percentage patterns (`%`, `เปอร์เซ็นต์`), unapproved monetary/rebate amounts (`บาท`, `USD`, `/lot`, `รวมเงินคืนทั้งสิ้น`), investment advice phrases, and token shapes, but natural-language paraphrasing of promises still relies on the `care` role prompt and `COO_Rules_MoonieXCare` escalation rules.
- **PR branch target:** Changes are committed by the worker launcher on the task branch (`agent/agy-task-881fec39`) for the PH / CTO reviewer to publish/merge to `main` via `kit/contabo/dfb41593-care-p1`.

## Blockers

- None.

## Skill learning

- `.claude/skills/COO_Rules_MoonieXCare/SKILL.md` (line 93) carries a pending field note: `the care role has no row in policies/agents.yaml yet, so audience uses worker; set audience to care when P1 adds the row`. Once this PR's `policies/agents.yaml` `care` role row is merged to `main`, `COO_Rules_MoonieXCare` can update `audience: [care]` and promote that field note.
