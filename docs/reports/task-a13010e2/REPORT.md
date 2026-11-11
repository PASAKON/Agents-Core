# REPORT task-a13010e2

## Files changed

- `tools/fal_image.py` — capped fal Seedream layerize and GPT Image 2.5 Flare edit CLI.
- `tests/test_fal_image.py` — mocked API-free unit coverage for pricing, quality rejection, cap refusal and default dry-run.
- `config/spend-tools.txt` — declares `tools/fal_image.py --max-usd` and documents its pricing reserve.

## What was done

- Added required `--job`, `--max-usd`, `--out`, `layerize`, and `edit` CLI options. `--fire` is required to make uploads or paid calls; otherwise the invocation is a dry-run.
- Reads PNG/JPEG/WebP dimensions locally to choose the Seedream area tier. Uses the task brief's per-layer price and layer maximum for the pre-send reserve. Seedream's current API schema has no layer-count input field, so `--max-layers` is used for pricing only.
- Prices Flare output by supported size and low/medium/high quality, plus $0.012 per reference. Rejects all other qualities and sizes.
- Uses the existing FAL_MEDIA_API_KEY_RW environment/Infisical source and does not print the key. Input paths must resolve under `/opt/MoonieXHQ/Work/`; uploads and image downloads are confined to fal storage URLs.
- Uses a locked `<job>.ledger.jsonl` under the work root and refuses before uploads when the ledger-inclusive cap would be exceeded.

## Validation

- `python3 -m compileall -q tools/fal_image.py tests/test_fal_image.py` — passed.
- `python3 -m pytest -q tests/test_fal_image.py` — could not run: `/usr/bin/python3` has no `pytest` module installed.
- No paid fal request was made.

## Not checked / risk

- Mocked unit tests need to be run in an environment with pytest installed.
- Seedream's documented schema returns a base image plus up to 16 separated layers but exposes no layer-count input. The worst-case cap reserve follows `--max-layers`; the API request cannot enforce that output count.
- This worker does not create or open a PR. The task launcher owns commit and push; PR creation remains outside this worktree workflow.

## Blockers

- `pytest` is unavailable in the worktree Python environment, so the requested unit tests were not executed.

## Skill learning

- Confirmed fal's official schemas: Seedream takes `image_url` and `prompt`, with output `layers`; Flare edit takes `image_urls`, `quality`, `image_size`, and returns PNG-capable `images`.
