# REPORT task-ddf3a651

## Files changed

- `tools/send_to_cxo.py`: append the requested quiet-letter notice to all three successful C-level send returns, after existing warnings. Use the effective explicit/body kind; leave Project Head delivery, stored letters, and wake behavior unchanged.
- `tools/node_dispatch.py`: with envelopes enabled, classify cross-host ask/blocker bodies as urgent using `mailbox.URGENT_KINDS`. Preserve CEO-relay urgency, stored kind `message`, and the envelope-off branch.
- `tests/test_mail_quiet_notice.py`: 23 cases covering explicit report, inferred fyi, blocker, local and both remote returns, envelopes on/off, Project Head reports, and cross-host ask/blocker/report storage and wake priority. State and wake calls are isolated with tmp_path and monkeypatch.
- `docs/reports/task-ddf3a651/REPORT.md`: this report.

## Validation

Ran the exact requested command (no additional `-q`):

```text
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_mail_quiet_notice.py tests/test_mail_envelope_letters.py tests/test_node_dispatch.py tests/test_node_dispatch_clevel_host.py
```

Result: **379 passed, 2 failed in 39.52s**. All 23 new test cases passed. The requested interpreter was accessible. No full-suite run was performed.

`git diff --check` passed.

## Blockers

- `tests/test_mail_envelope_letters.py:1171`, `test_node_dispatch_fyi_and_report_from_another_host_never_wake_a_c_level_box[True]`, explicitly expects cross-host ask mail to remain normal and not wake. This contradicts the requested urgent behavior. The test file is outside the explicit diff allowlist, so its assertion has been left unchanged. Requested authorization to update that assertion; no approval received when this report was written.
- `tests/test_mail_envelope_letters.py:885`, `test_a_read_dir_owned_by_another_user_is_not_used`, fails because the sandbox rejects `os.chown(rd, 65534, 65534)` with `OSError: [Errno 22] Invalid argument`. This prevents validation of that ownership test here.
- The all-four-files-pass acceptance criterion is therefore not met. No tests were skipped, suppressed, or altered to hide these failures.

## Skill learning

- (none)
