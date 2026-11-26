# REPORT task-f945e638

## Summary
- **Branch:** `agent/agy-task-f945e638`
- **Task:** Build MoonieX Care S2 (LINE OA Manager browser sender) OFFLINE per `docs/design/mooniex-care.md` (§2–§5), building on S1 (`PR #798`) and reusing `lib/care/` outbox and quota APIs.
- **Key Features Implemented:**
  1. **Channel Check & Recipient Readback (`lib/care/browser_sender.py`):** Verifies the active OA header matches `MoonieX Officials` / `@mooniex` / `@587kfqpt` and the active chat header matches `care_outbox.recipient_id` and `care_outbox.recipient_display_name` before staging or claiming `sending`. Fails closed (`state='failed'`, `channel_check_mismatch` or `recipient_readback_mismatch`) on any mismatch.
  2. **Pre-Click `sending` Transition (`Outbox.claim_sending(row_id, "oa_browser")`):** Atomically marks the outbox row `state='sending'` (`delivery_via='oa_browser'`, `sending_started_at=NOW()`) **before** `driver.click_send()` executes, and never auto-retries rows already in `sending`.
  3. **Throttle Per-Hour & Per-Day Ceilings (`decide_browser_throttle`, `config/care.yaml`):** Evaluates rolling 1-hour and 24-hour `oa_browser` send counts against `browser_sender.hourly_ceiling` and `browser_sender.daily_ceiling`, deferring excess rows (`state='deferred'`, `throttle_hourly_ceiling` / `throttle_daily_ceiling`). Preserves `null` (`None`) placeholders in `config/care.yaml` for TBD ceilings and `cdp_port`.
  4. **Human-Like Jittered Pacing (`PacingConfig`, `JitterPacer`):** Applies randomized, non-uniform delays before thread selection (`pre_open`), during typing/staging proportional to message character length (`stage_typing`), and after clicking Send (`cooldown`).
  5. **Kill Switch (`captcha`, `warning`, `logout`, `ui_selector_missing`):** Inspects DOM snapshots before and after actions, halts immediately on any trigger, sets persistent `care_sender_enabled = "false"` in `care_state`, alerts the COO once (deduplicated via `care_sender_kill_alerted`), forbids any login attempt, and never auto re-enables (requires explicit `manual_reenable_sender(outbox, operator_id=...)`).
  6. **Fallback to Reply-Token Path When Sender Is Off:** When `care_sender_enabled == "false"`, skips all browser interactions; delivers immediately via `POST /v2/bot/message/reply` (`delivery_via='api_reply'`) if a valid `reply_token` is present, or marks the row `state='fallback'` until a fresh webhook `reply_token` is attached (`Outbox.attach_reply_token`) and fulfilled via `CareSender` / `BrowserSender`.
  7. **Sanitized Offline DOM Fixtures & S2 Test Suite:** Added four PII-free, token-free DOM fixtures (`normal_chat.html`, `captcha.html`, `warning.html`, `logout.html`) under `tests/fixtures/care_dom/` and comprehensive unit tests in `tests/test_care_s2.py`. Did not edit `docs/design/mooniex-care.md`.

## Files Changed
- `config/care.yaml` — Extended `browser_sender` section with S2 channel identity and pacing defaults while preserving `null` placeholders for `hourly_ceiling`, `daily_ceiling`, and `cdp_port`.
- `lib/care/outbox.py` — Added `attach_reply_token()` for webhook reply-token fallback on `queued`/`deferred`/`fallback` rows, allowed `claim_sending(..., "api_reply")` from `fallback` state, and added `count_browser_sends_since()` for rolling hourly/daily throttle windows.
- `lib/care/browser_sender.py` — New offline S2 OA Manager browser sender module (`BrowserSenderConfig`, `PacingConfig`, `JitterPacer`, `ThrottleDecision`, `decide_browser_throttle`, `DomInspection`, `inspect_oa_dom`, `verify_channel`, `verify_recipient`, `FixtureBrowserDriver`, `BrowserSender`, `manual_reenable_sender`).
- `lib/care/sender.py` — Integrated `CareSender` with `care_sender_enabled` kill-switch state, `fallback` reply-token fulfillment, and optional `browser_sender` delegation while preserving full S1 backwards compatibility.
- `lib/care/__init__.py` — Exported S1 and S2 public interfaces.
- `tests/fixtures/care_dom/normal_chat.html` — Sanitized synthetic `chat.line.biz` normal conversation DOM fixture for `MoonieX Officials` (`@mooniex` / `@587kfqpt`).
- `tests/fixtures/care_dom/captcha.html` — Sanitized synthetic CAPTCHA challenge DOM fixture.
- `tests/fixtures/care_dom/warning.html` — Sanitized synthetic OA Manager automated activity warning DOM fixture.
- `tests/fixtures/care_dom/logout.html` — Sanitized synthetic `account.line.biz` expired session / login redirect DOM fixture.
- `tests/test_care_s2.py` — Offline S2 unit test suite (12 test cases including parametrized `captcha`/`warning`/`logout` kill-switch tests).

## Validation Performed
- Executed the offline S1 + S2 pytest suites locally via `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -o addopts= -v tests/test_care_s1.py tests/test_care_s2.py`:

```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.4.2, pluggy-1.6.0 -- /opt/MoonieXHQ/Agents/Core/.venv/bin/python
cachedir: .pytest_cache
rootdir: /opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-f945e638
configfile: pytest.ini
plugins: anyio-4.15.1, platformdirs-4.12.0
collecting ... collected 26 items

tests/test_care_s1.py::test_idempotent_enqueue PASSED                    [  3%]
tests/test_care_s1.py::test_claim_is_atomic_and_before_send PASSED       [  7%]
tests/test_care_s1.py::test_reply_path_free_no_quota_read PASSED         [ 11%]
tests/test_care_s1.py::test_reply_rejected_reroutes PASSED               [ 15%]
tests/test_care_s1.py::test_care_reply_after_expiry_never_pushes PASSED  [ 19%]
tests/test_care_s1.py::test_announcement_push_after_expiry PASSED        [ 23%]
tests/test_care_s1.py::test_alert_once_at_240 PASSED                     [ 26%]
tests/test_care_s1.py::test_hard_stop_and_reserve PASSED                 [ 30%]
tests/test_care_s1.py::test_hard_stop_defers_row PASSED                  [ 34%]
tests/test_care_s1.py::test_429_halts_month PASSED                       [ 38%]
tests/test_care_s1.py::test_dry_run_sends_nothing PASSED                 [ 42%]
tests/test_care_s1.py::test_network_error_not_retried PASSED             [ 46%]
tests/test_care_s1.py::test_token_never_stored PASSED                    [ 50%]
tests/test_care_s2.py::test_config_placeholders_remain_null PASSED       [ 53%]
tests/test_care_s2.py::test_sanitized_dom_fixtures_classification_and_hygiene PASSED [ 57%]
tests/test_care_s2.py::test_normal_chat_channel_check_readback_and_mark_sending_before_click PASSED [ 61%]
tests/test_care_s2.py::test_channel_check_mismatch_aborts_before_sending_and_click PASSED [ 65%]
tests/test_care_s2.py::test_recipient_readback_mismatch_aborts_before_sending_and_click PASSED [ 69%]
tests/test_care_s2.py::test_missing_ui_selector_fails_closed_and_trips_kill_switch PASSED [ 73%]
tests/test_care_s2.py::test_kill_switch_on_captcha_warning_logout_alerts_once_and_no_auto_reenable[captcha-captcha.html] PASSED [ 76%]
tests/test_care_s2.py::test_kill_switch_on_captcha_warning_logout_alerts_once_and_no_auto_reenable[warning-warning.html] PASSED [ 80%]
tests/test_care_s2.py::test_kill_switch_on_captcha_warning_logout_alerts_once_and_no_auto_reenable[logout-logout.html] PASSED [ 84%]
tests/test_care_s2.py::test_fallback_to_reply_token_path_when_sender_is_off PASSED [ 88%]
tests/test_care_s2.py::test_throttle_per_hour_and_per_day_ceilings PASSED [ 92%]
tests/test_care_s2.py::test_human_like_jittered_pacing_non_uniform_and_proportional PASSED [ 96%]
tests/test_care_s2.py::test_crash_recovery_skips_stuck_sending_and_no_pii_or_token_in_db PASSED [100%]

============================== 26 passed in 0.81s ==============================
```
- Confirmed `docs/design/mooniex-care.md` is unmodified and zero live browser, winbox, relay-inventory, CDP port, login, secret, customer text, or MT5 interactions exist.

## Limitations
- Purely offline implementation against sanitized DOM fixtures as specified; `cdp_port`, `hourly_ceiling`, and `daily_ceiling` remain `null` (`None`) placeholders in `config/care.yaml` pending live OA confirmation.

## Blockers
- (none)

## Skill learning
- (none)
