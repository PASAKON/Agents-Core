# REPORT task-d9ef8436

Implemented an offline-by-default, zero-model Champa image runner. No live Chrome,
Champa, network generation, or credit spend was used during development.

## Files changed

- `scripts/champa/champa_image.py`: JSON input validation, image settings, strict
  submit-price check, required per-run credit cap, post-submit balance check,
  resume ledger, manual-history harvest, image validation/conversion, tab cleanup.
- `tests/test_champa_image.py`: offline fake adapter/CDP acceptance and edge tests.
- `config/spend-tools.txt`: declares the image runner's `--max-credits` cap.
- This report.

The video runner and existing guard are unchanged. The image runner imports their
argument parser, cap parser, price/balance parsing, base page adapter, cleanup,
ledger writes and queue accounting. CDP selection follows the video runner with
an image adapter and cleanup on navigation failure. Only tab IDs are printed.

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
output-directory lock prevents concurrent invocations racing the ledger. Each
attempt is recorded and fsynced before clicking: an ambiguous/failed click leaves
a reservation and is not retried automatically. Keep the ledger and use the same
output directory on resume. The inherited queue limit is eight unfinished jobs;
harvest between batches to free slots.

## Validation performed

Command (using the required venv interpreter; no `-q` added):

```bash
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_champa_image.py tests/test_champa_fire.py tests/test_champa_queue_guard.py
```

Initial run: 56 passed. Final run after four additional edge tests: **60 passed
in 1.68s**. `git diff --check` passed.
Tests cover offline dry-run, missing/invalid cap, price mismatch, per-run cap,
balance changes, duplicate/unsafe names, submitted/done resume, interrupted clicks,
manual history, image conversion/rejection, damaged ledger, concurrent runner
refusal, fake CDP reuse and navigation-failure cleanup.

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
  Playwright and Pillow. The concurrency lock uses POSIX `fcntl`; native Windows
  is not supported by this implementation.
- As with the video runner, an existing Champa tab is reused and never closed;
  only a tab created by this runner is closed. The browser itself stays open.
- Deduplication is scoped to the retained output ledger, not other directories or
  manually submitted history until that history is harvested.

## Blockers

- None for implementation or offline validation. Live verification was explicitly
  prohibited and remains outstanding. No git add/commit was run.

## Skill learning

- Shared video ledger records can also provide image resume accounting, but paid
  image jobs need a separate price guard: `QueueGuard.check()` intentionally
  accepts only free Unlimited jobs. Evidence: unchanged video/guard tests pass
  alongside image price/cap tests.
- Record submission intent before browser clicks to avoid retries after ambiguous
  failures. Evidence: `test_uncertain_click_is_never_retried`.
