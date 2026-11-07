# PH brain fallback KeyError

## Findings and fix

At base commit `2ade542c`, `tools/ph_brain.py:main` indexed `res["fallback_triggered"]` while formatting a successful turn. This is the only production reader found by repository search. A successful result missing that field reaches the top-level exception handler and prints exactly `ph_brain error: 'fallback_triggered'`.

The current `run_turn` success return already includes the field. Its timeout return omitted it, but the current CLI's non-ok branch bypasses the unsafe read. Therefore the checked-out code does not establish an unmodified end-to-end path from a timeout to the reported KeyError. `tools/agy_takeover.py` handoff-to-brain calls `run_turn` and does not read this field. Exhausting all models raises RuntimeError rather than returning another result dictionary.

The fix uses `res.get("fallback_triggered")` at the CLI reader and provides the field in both `run_turn` return dictionaries. Fallback calculation is shared before invocation so a timeout on a retried or forced fallback model reports the same semantics as success. Unrelated state, invocation, delegation, and status dictionaries are not turn results and are unchanged.

Rule 6 in `roles/ph_shell.md` now explicitly requires the Haiku shell itself to send the blocker letter, includes the verified positional CLI syntax and owner routing, permits a GitHub issue on PASAKON/Agents-Core, and exempts these outage actions from rule 4's brain-only restriction.

## Validation

- Before changing production code, ran `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_ph_brain.py`: **3 failed, 8 passed** against the unchanged main-based implementation.
- The CLI regression mocks `invoke_agy`, runs real `run_turn`, then deliberately removes optional metadata at the result boundary to simulate a legacy/alternate producer. It reproduces the exact reported stderr. This is a defensive boundary reproduction, not proof that current production success results naturally omit the field.
- Two additional failing cases cover actual incomplete timeout returns: first attempt and timeout after a quota failure.
- After the fix, the same command: **11 passed**. No `-q` argument was supplied (repository pytest defaults produce compact output).
- `git diff --check`: passed. No real AGY invocation or quota spend.

## Not checked / risk

- Live PH#999899b1 state and deployed source were not inspected or modified. The reported turn count and alternating fallback events are incident context, not independently verified observations.
- The deployed version/result producer responsible for a successful result missing metadata remains unconfirmed. This patch hardens the boundary and completes the timeout contract; it does not establish the cause of model oscillation or change model selection.
- No live mailbox delivery, GitHub issue creation, worker delegation, or AGY takeover was exercised.
- Commit/push belong to the launcher after worker completion. PR creation to main remains pending publication of the task branch; see the task report and PR body.
