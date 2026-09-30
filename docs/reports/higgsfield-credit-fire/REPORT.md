# Higgsfield Credit Fire Report

## Status
Complete. All gates passed.

### What was built
1. `scripts/higgsfield/credit_guard.py`:
   - Pure Python zero-model module (no Playwright dependency).
   - `parse_price(label)` parses charged price from button text (last integer; "Unlimited" without numbers = 0; unreadable / purchase words = None).
   - `SpendRefused` custom exception for spending refusals.
   - `SpendGuard` class enforcing positive caps for `max_per_clip` and `budget`, persistent JSONL ledger tracking via `spent()` and `recorded_clip_ids()`, in-memory verification in `check(label)`, and post-spend ledger appending with balance-delta validation in `record(clip_id, price, balance_before, balance_after)`.

2. `scripts/higgsfield/credit_fire.py`:
   - CLI runner supporting `--prompts`, `--cdp`, `--out`, `--dry-run`, `--fire`, `--max-per-clip`, `--budget`, `--duration`, `--ratio`, `--resolution`, and `--limit`.
   - Returns strict exit codes (0: done, 2: bad arguments, 3: SpendRefused, 4: page problem, 5: clip not finished).
   - `--fire` requires both positive caps (`--max-per-clip` and `--budget`) before any browser/CDP connection is attempted.
   - Page handling attaches to existing `higgsfield.ai/ai/video` page across browser contexts or navigates a new page; closes only pages opened by the runner.
   - Money rules: exactly one submit-click call site in the file (`adapter.click_submit()`), zero retry clicks, strict sequence (read settings -> type prompt -> read label -> guard.check -> newest_ts -> click_submit -> guard.record -> poll_for_result -> download).
   - Zero occurrences of `role=switch`, zero occurrences of `drive_upload`, no `.env` reads.
   - `ComposerPage` adapter allows complete offline injection in tests.

3. `tests/test_higgsfield_credit_fire.py`:
   - Offline tests utilizing `FakeComposerPage`.
   - Tests dry-run zero submit clicks and zero prompt typing.
   - Tests `--fire` with caps on 3 clips makes exactly 3 clicks and downloads.
   - Tests poll timeout on clip 1 makes exactly 1 click total and returns exit code 5.
   - Tests label above `--max-per-clip` makes 0 clicks and returns exit code 3.
   - Tests clips already present in ledger are skipped on resume.
   - Tests existing open pages are not closed upon run completion.
   - Tests settings mismatch and missing prompt textbox trigger exit code 4 with 0 clicks.
   - Tests budget exhaustion stops run with exit code 3.
   - Tests `--limit` flag.

### Test Commands and Results
- Test command:
  `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_higgsfield_credit_guard.py tests/test_higgsfield_credit_fire.py -v`
- Last output line:
  `======================== 33 passed, 1 warning in 0.19s =========================`

- Gen loop compatibility test command:
  `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_higgsfield_gen_loop.py -q`
- Last output line:
  `12 passed, 1 warning in 0.05s`

- Diff verification:
  `git diff main -- tests/test_higgsfield_credit_guard.py scripts/higgsfield/gen_loop.py`
  (empty diff)

- Grep verification:
  `grep -E "role=switch|drive_upload" scripts/higgsfield/credit_fire.py scripts/higgsfield/credit_guard.py`
  (exit code 1, zero matches)

### Anything could not do
None. All requirements implemented and verified.

## Iteration 1 Update (CTO Feedback)
### What was changed
1. `scripts/higgsfield/credit_fire.py`:
   - Added `wait_for_price(adapter, timeout_s, poll_interval_s)` helper with `WAIT_PRICE_TIMEOUT_S = 5.0` and `WAIT_PRICE_POLL_S = 0.5`.
   - In `--dry-run`, per clip: types the prompt with `adapter.type_prompt(prompt)`, waits up to 5 s (polling every 0.5 s) until `parse_price(read_label()) is not None`, then formats and prints the DRY line as before (`DRY clip_id=<id> price=<n> would_fire=<yes|no> reason=<...>`). Dry-run never calls `click_submit` and never writes the ledger.
   - If the label never parses in dry-run, reports `would_fire=no reason=unreadable label` with `price=None`.
   - In the `--fire` path: after `adapter.type_prompt(prompt)`, uses `wait_for_price(adapter)` before `guard.check(label)`. If it never parses, prints page problem and exits with code 4 with zero submit clicks.
   - Exactly one submit-click call site maintained, zero `role=switch`, zero `drive_upload`.

2. `tests/test_higgsfield_credit_fire.py`:
   - Updated `FakeComposerPage` to support before/after typing labels, returning "Generate" before typing and "Generate 80 60" after typing (using sentinel `_UNSET` to allow explicit `label=None` or `label="Generate"`).
   - Added `label_delay_polls` support in `FakeComposerPage` to simulate delayed label updates.
   - Added `fast_wait_price` autouse fixture to accelerate test timeouts offline.
   - Renamed and updated `test_dry_run_makes_zero_submit_clicks_and_zero_typing` to `test_dry_run_types_but_makes_zero_submit_clicks`: verifies fake label returns "Generate" before typing and "Generate 80 60" after typing, prompt typing occurs per clip, zero submit clicks are made, and spend ledger is not created.
   - Updated `test_dry_run_with_caps_simulates_in_memory` to expect typed prompts in dry-run.
   - Added `test_label_never_gets_price_dry_run_reports_unreadable_and_fire_returns_4`: verifies dry-run prints `would_fire=no reason=unreadable label`, and fire returns exit code 4 with zero clicks.
   - Added `test_wait_for_price_polls_until_label_updates` to verify polling until label updates.

3. Protected files `tests/test_higgsfield_credit_guard.py` and `scripts/higgsfield/gen_loop.py`:
   - Verified untouched (`git diff main` is empty).

### Test Commands and Results
- Test command:
  `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_higgsfield_credit_guard.py tests/test_higgsfield_credit_fire.py -v`
- Last output line:
  `======================== 35 passed, 1 warning in 0.58s =========================`

## Skill learning
- (none)
