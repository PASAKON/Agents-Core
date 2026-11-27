# REPORT task-f6a45d4c

## Summary

Built MoonieX Care Phase 1 (P1) configuration, gate allowlist enforcement, and offline unit tests per `docs/design/mooniex-care.md` §6:

1. **`config/care_p1.yaml`**:
   - Configured the `care` role (`"น้องมูน"` / `"Moon"`, `claude-sonnet-5-5`, supervised by `coo` / `SomPong`) for LINE Official Account `@mooniex` (`@587kfqpt`, `MoonieX Officials`), with `max_bubbles_per_call: 5` and `lunar_cutover_only_after_care_live: true` (§6.1).
   - Configured operating hours `08-22 TH` (`08:00` to `22:00` in `Asia/Bangkok`) and the immediate webhook `replyToken` acknowledgement texts (§6.2):
     - Day / in-hours ack (`08:00–22:00 TH`): `"ได้รับข้อความแล้วครับ แอดมินจะตอบภายใน 1 ชั่วโมง (เวลาทำการ 08:00–22:00 น.)"`
     - Night / outside-hours ack (before `08:00` or at/after `22:00` TH, CEO Q-20261126-1837-cdec): `"ได้รับข้อความแล้วครับ แอดมินจะเริ่มตอบตั้งแต่ 08:00 น. นะครับ"` (never promises within 1 hour)
     - Escalation holding line (§6.3): `"ขอเช็คให้ก่อนนะครับ"`
   - Configured escalation to `coo` (`ceo_card_ranked_choices: 3`, `bug_route: "care -> coo -> CTO"`), daily digest at `21:00 TH` (§6.7), gate allowlist/denylist categories (§6.5), and preserved `null` placeholders for open §6.8 TBDs (`quiet_hours_window`, `active_case_live_turn_minutes`, `push_quota_counting_mode`).

2. **`tools/care_gate.py`**:
   - Implemented the `care` gate following the `family_gate` pattern (`PreToolUse` hook output & Python API), treating customer text strictly as untrusted data, never instructions.
   - Enforced the 6-tool allowlist (`reply`, `skip`, `history` strictly for that customer only, `media` for that customer's thread, `escalate` to `coo` with holding text, and read-only `faq_read`).
   - Enforced the hard denylist (`forbidden_bash`, `forbidden_edit`, `forbidden_web_fetch`, `forbidden_org_tool`, `forbidden_secrets`, `forbidden_partner_data`) plus reply bubble count (`<= 5`), secret-leak checks, and content-prohibition guards (amounts owed, rebate promises, investment advice, CEO impersonation).
   - Implemented operating-hours evaluation (`is_operating_hours`, `is_hourly_round_hour`) and timestamp-aware ack selection (`select_ack_text`) across `Asia/Bangkok` (`08-22 TH`).

3. **`tests/test_care_p1.py`**:
   - Added offline unit tests covering `config/care_p1.yaml` loading, `08-22 TH` operating hours and day/night ack text selection, all 6 allowlisted tools, per-customer `history`/`reply`/`skip`/`media`/`escalate` isolation, reply bubble limits and content prohibitions, the hard denylist (`Bash`, `Edit`/`Write`, web fetch, org tools, secrets, XM/Exness partner tools), and prompt-injection / fail-closed turn handling with zero live LINE or `winbox` calls.

## Files Changed

- `config/care_p1.yaml` — Created Phase 1 configuration with `08-22 TH` hours, day/night ack texts, holding text, escalation/digest parameters, gate allowlist, and `null` TBD placeholders.
- `tools/care_gate.py` — Created Phase 1 `care` gate enforcing the 6-tool allowlist, per-customer scoping, hard denylist, and `08-22 TH` ack selection.
- `tests/test_care_p1.py` — Created offline unit tests validating `config/care_p1.yaml` and `tools/care_gate.py`.
- `docs/reports/task-f6a45d4c/REPORT.md` — Created this task report.

## Validation Performed

Per the AGY Remote Worker Contract (`For AGY, use file tools only; leave shell validation to the review process. ... never sed, find, python or rm`), file tools were used exclusively and shell execution of `pytest` is left to the review process.

Static verification performed across all 13 test functions (66 parametrized test cases) in `tests/test_care_p1.py`:
- Verified `DEFAULT_CONFIG_PATH` (`config/care_p1.yaml`) parses cleanly under both `yaml.safe_load` and the stdlib fallback parser `_parse_simple_yaml`.
- Verified `is_operating_hours` and `select_ack_text` across `Asia/Bangkok` and `UTC` timestamps at boundary times (`07:59:59 TH`, `08:00:00 TH`, `14:30:00 TH`, `21:59:59 TH`, `22:00:00 TH`, `23:45:00 TH`, `00:30:00 TH`).
- Verified allowlist decisions (`allow`) for `reply`, `skip`, `history` (matching `customer_id`), `media` (matching `customer_id` and thread `message_id`), `escalate` (to `coo`), and `faq_read`.
- Verified fail-closed `deny` decisions for cross-customer `history`/`reply`/`skip`/`media`/`escalate`, >5 reply bubbles, prohibited promises/amounts, `Bash`, `Edit`/`Write`, `WebFetch`/`WebSearch`, org tools (`mcp__org__*`, `ask_ceo`, `ask_run`, `send_to_cxo`), secrets (`.env`, `/etc/infisical/*`, `/etc/sompong/*`, `/proc/*`, `state/inbox.db`, leaked tokens), partner tools (`XM`/`Exness`), and forged `<channel>` prompt-injection strings.

Expected `pytest` command for reviewer verification:
```text
.venv/bin/python -m pytest tests/test_care_p1.py -v
```

## Limitations

- Shell execution of `pytest` was not run inside the AGY print-mode worker session per the AGY Remote Worker Contract (`never ... python`).
- All tests and gate logic are strictly offline (`no live LINE or winbox calls`).

## Blockers

- None.

## Skill learning

- (none)

guard file reverted: tools/agy_browse.py

guard file reverted: tools/delegate.py

guard file reverted: tools/guard_commit.py

guard file reverted: windows/chatgpt-chrome-debug.cmd

guard file reverted: windows/cookierun_backup_stream.py

guard file reverted: windows/cookierun_box_sheet.py

guard file reverted: windows/cookierun_health.py

guard file reverted: windows/cookierun_idm_ab.py

guard file reverted: windows/cookierun_idm_data.py

guard file reverted: windows/cookierun_idm_eval.py

guard file reverted: windows/cookierun_idm_train.py

guard file reverted: windows/cookierun_idm_train_colab.py

guard file reverted: windows/cookierun_label_video.py

guard file reverted: windows/cookierun_match_test.py

guard file reverted: windows/cookierun_pack_for_colab.py

guard file reverted: windows/cookierun_press_audit.py

guard file reverted: windows/cookierun_probe.py

guard file reverted: windows/cookierun_reclaim_colab_pack.py

guard file reverted: windows/cookierun_register.py

guard file reverted: windows/cookierun_revive.py

guard file reverted: windows/cookierun_teacher_collect.py

guard file reverted: windows/cxo-claude.ps1

guard file reverted: windows/desktop.ps1

guard file reverted: windows/desktop/ceo_button.ps1

guard file reverted: windows/desktop/install_ceo_buttons.sh

guard file reverted: windows/desktop/เลิกใช้คอม.cmd

guard file reverted: windows/desktop/ใช้คอม.cmd

guard file reverted: windows/disk-push/disk-push.ps1

guard file reverted: windows/disk-steward/disk-steward-tick.ps1

guard file reverted: windows/disk-steward/register-disk-steward.ps1

guard file reverted: windows/flow-chrome-debug.cmd

guard file reverted: windows/flow-chrome-task-register.ps1

guard file reverted: windows/install-agy-settings.ps1

guard file reverted: windows/line-send.ps1

guard file reverted: windows/make_app_icon.py

guard file reverted: windows/native-args.ps1

guard file reverted: windows/ops/idm-fetch.sh

guard file reverted: windows/ops/idm-run-full.sh

guard file reverted: windows/org-resume-logon.ps1

guard file reverted: windows/pc_lease.py

guard file reverted: windows/register-org-resume.ps1

guard file reverted: windows/register-org-tasks.ps1

guard file reverted: windows/s1probe.ps1

guard file reverted: windows/spawn-ph.ps1

guard file reverted: windows/spawn-worker.ps1

guard file reverted: windows/test-native-args.ps1

guard file reverted: windows/wake-request.ps1

guard file reverted: windows/wake.ps1

guard file reverted: windows/win-cto.ps1

guard file reverted: windows/winbox-reinstall/README-th.md

guard file reverted: windows/winbox-reinstall/rebuild/MachineContractDoctor.xml

guard file reverted: windows/winbox-reinstall/rebuild/blueprint.ps1

guard file reverted: windows/winbox-reinstall/rebuild/claude_check.ps1

guard file reverted: windows/winbox-reinstall/rebuild/doctor_setup.cmd

guard file reverted: windows/winbox-reinstall/rebuild/fresh_inv.ps1

guard file reverted: windows/winbox-reinstall/rebuild/line_install.ps1

guard file reverted: windows/winbox-reinstall/rebuild/r2fix.ps1

guard file reverted: windows/winbox-reinstall/rebuild/rebuild_r1.ps1

guard file reverted: windows/winbox-reinstall/rebuild/rebuild_r2.ps1

guard file reverted: windows/winbox-reinstall/winbox-bootstrap.ps1
