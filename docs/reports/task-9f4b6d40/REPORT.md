# REPORT task-9f4b6d40

## Changes
- `tools/chatgpt_images.py`: added Library deletion before the existing conversation hide operation, at the scheduler's existing continuation-safe cleanup point. Only `kind=file` nodes with the exact current conversation ID are selected. Missing IDs fail closed; there is no newest-file fallback.
- Authentication stays inside page JavaScript. Only an integer deletion count/error sentinel crosses into Python; backend exceptions are sanitized.
- Added `--keep-in-chatgpt` to skip both cleanup steps. Successful image rows start with `deleted_from_chatgpt: 0`; the row triggering cleanup records the acknowledged batch count. Earlier continuation rows remain zero because cleanup was deferred.
- Cleanup failure preserves the saved PNG and done status. Library failure prevents hiding; a hide failure preserves the successful deletion count.
- `tests/test_chatgpt_images.py`: mocked coverage for exact file selection, unrelated/missing thread IDs, rejected deletion, token non-disclosure, flag propagation, deletion-before-hide order, continuation deferral, and PNG preservation on either cleanup failure. Page JavaScript executes under Node with mocked fetch.
- Read the CTO stash diff without applying, popping, or dropping it.

## Validation
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_chatgpt_images.py -q`: all 74 tests passed, including all pre-existing image tests.
- `git diff --check`: passed.
- Broader repository suite reported multiple failures and was interrupted. Diagnostic rerun with `python -m pytest --lf -x --tb=short` stopped with 1 failed, 81 passed, 1 skipped: `scripts/test_dev_tab_color.py::test_zero_in_flight_does_no_api_work` raises `RuntimeError: tests must not touch a real checkout's tasks.db (ADR 0021)` in `lib/db.py:490`. These files are outside this change; the DB safety guard was not bypassed.
- System `python` is unavailable and system `python3` lacks pytest; used the existing repository virtual environment.

## Not checked / risk
- No live browser/API calls or image generation performed. CMO owns the winbox live test: verify saved PNG, matching Library files removed, chat hidden, unrelated Library files retained, and the keep flag retaining both files and chat.
- Uses the stash's Library endpoint and response schema. Live pagination and per-file partial-success behavior are not established here; the count is the submitted matching batch size after HTTP success, not a separate post-deletion verification.
- New JavaScript execution tests require Node on the test host.
- Recovery mode retains its existing behavior; this change extends the scheduler cleanup path only.

## Blockers
- None for implementation or targeted tests. Cannot claim a green repository-wide suite because the unrelated DB test hits the checkout safety guard; remaining full-suite failures were not investigated.

## Skill learning
- (none)
