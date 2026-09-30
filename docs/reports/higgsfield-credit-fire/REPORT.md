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

## Skill learning
- (none)
