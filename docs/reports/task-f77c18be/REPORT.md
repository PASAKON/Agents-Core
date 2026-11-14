# REPORT task-f77c18be

Implemented an offline-by-default, zero-model Champa image runner (continued from
`task-d9ef8436`, commit `67e52e75`) with portable POSIX (`fcntl`) and native Windows
(`msvcrt.locking`) single-run locking. No live Chrome, Champa, network generation, or
credit spend was used during development.

## Files changed

- `scripts/champa/champa_image.py`: JSON input validation, image settings, strict
  submit-price check, required per-run credit cap, post-submit balance check,
  resume ledger (`"ab"` stream for cross-platform `os.fsync`), portable non-blocking
  output-directory lock (`fcntl.flock` on POSIX, `msvcrt.locking` with `LK_NBLCK` /
  `LK_UNLCK` on byte 0 on Windows), manual-history harvest, image validation/conversion,
  and tab cleanup.
- `tests/test_champa_image.py`: offline fake adapter/CDP acceptance and edge tests,
  including `test_windows_ledger_lock_and_refusal` exercising the Windows `msvcrt.locking`
  branch via `monkeypatch`.
- `config/spend-tools.txt`: declares the image runner's `--max-credits` cap.
- `docs/reports/task-f77c18be/REPORT.md`: this report (moved from `task-d9ef8436` and
  updated with the Windows lock portability fix).

The video runner (`scripts/champa/champa_fire.py`) and existing queue guard
(`scripts/champa/queue_guard.py`) are unchanged and verified free of POSIX-only imports.
The image runner imports their argument parser, cap parser, price/balance parsing, base
page adapter, cleanup, ledger writes and queue accounting. CDP selection follows the
video runner with an image adapter and cleanup on navigation failure. Only tab IDs are
printed.

## Usage

Run with `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` as `python` below.
Input is a JSON list, for example:

```json
[{"name":"r5-ui-kit","prompt":"A complete interface design kit"}]
```

```bash
python scripts/champa/champa_image.py --prompts round5.json --out output/images
python scripts/champa/champa_image.py --prompts round5.json --out output/images --fire --max-credits 6
python scripts/champa/champa_image.py --prompts round5.json --out output/images --harvest
```

Defaults: `--cdp http://127.0.0.1:9280`, `--model "Nano Banana 2"`,
`--ratio 16:9`, `--resolution 1K`, `--expected-credits 2`. Dry-run does not
connect, fill the composer, or write the ledger. Fire and harvest are mutually
exclusive. Harvest checks full prompt text, including manually created images.
PNG/JPEG/WebP content is decoded and saved as an actual PNG, then marked done.

Exit codes: 0 completed; 2 invalid arguments/input; 3 cap/price/queue/balance
guard refusal; 4 page, download, or ledger failure. Reaching the cap with pending
items exits 3; completing all eligible inputs within the cap exits 0.

`<out>/image_queue.jsonl` retains the shared `clip_id` field for image names.
Submitted and done names are never resubmitted within this ledger. An exclusive
non-blocking output-directory lock (`fcntl.flock` on POSIX, `msvcrt.locking` on
native Windows) prevents concurrent invocations racing the ledger. Each
attempt is recorded and fsynced before clicking: an ambiguous/failed click leaves
a reservation and is not retried automatically. Keep the ledger and use the same
output directory on resume. The inherited queue limit is eight unfinished jobs;
harvest between batches to free slots.

## Validation performed

- Inspected `scripts/champa/queue_guard.py`, `scripts/champa/champa_fire.py`, and
  `scripts/champa/champa_image.py` to confirm no POSIX-only imports remain on the
  import path (`fcntl` falls back cleanly to `msvcrt.locking` on Windows, and
  `ImageGuard.record_submit` opens the ledger with `"ab"` so `os.fsync` has write
  access on Windows as well as POSIX).
- Added `test_windows_ledger_lock_and_refusal` in `tests/test_champa_image.py` to
  exercise the Windows `msvcrt.locking` branch (`LK_NBLCK` acquisition, non-blocking
  `OSError` -> `Refused` exit 3 when held, and `LK_UNLCK` release) via `monkeypatch`.
- Verified `git diff --check` and `git status` clean formatting (shell test execution
  left to the review process per the AGY Remote Worker Contract:
  `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_champa_image.py tests/test_champa_fire.py tests/test_champa_queue_guard.py`).

## Not checked / risk

- Selectors are unverified against the live page. Model/ratio/resolution menus,
  selected image tab, history card structure and download links may need adjustment.
  Missing or ambiguous controls stop the runner rather than guessing.
- Harvest covers history currently rendered by the page; it does not paginate or
  scroll old history. Exact full prompt text and an available download link are
  required. It never submits to replace missing results.
- Balance is reread after each click with a one-second UI settling delay. Delayed
  provider billing or stale UI balance cannot prove final billed cost. The cap
  limits attempted spend based on the displayed, checked price; an unexpected
  provider charge can only be detected after the click.
- Real browser adapter paths and downloads were not exercised. Runtime requires
  Playwright and Pillow.
- As with the video runner, an existing Champa tab is reused and never closed;
  only a tab created by this runner is closed. The browser itself stays open.
- Deduplication is scoped to the retained output ledger, not other directories or
  manually submitted history until that history is harvested.

## Blockers

- None. Live verification was explicitly prohibited. Under the AGY Remote Worker
  Contract, file tools were used and shell pytest execution is left to the review
  process. No `git add` or `git commit` was run.

## Skill learning

- Shared video ledger records can also provide image resume accounting, but paid
  image jobs need a separate price guard: `QueueGuard.check()` intentionally
  accepts only free Unlimited jobs. Evidence: `ImageGuard.check_paid` and
  `test_wrong_price_refused` in `tests/test_champa_image.py`.
- Record submission intent before browser clicks to avoid retries after ambiguous
  failures, and open the ledger in append-binary (`"ab"`) mode before `os.fsync` so
  Windows `FlushFileBuffers` has write access alongside portable `fcntl`/`msvcrt.locking`
  directory locking. Evidence: `ImageGuard.record_submit`, `ledger_lock`, and
  `test_windows_ledger_lock_and_refusal` in `tests/test_champa_image.py`.
