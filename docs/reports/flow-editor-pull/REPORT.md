# Flow editor pull repair

## Files changed

- `tools/flow_shoot.py`: 720p pull opens the matched `flow-video-tile` editor, records its clip ID, mutes media, downloads the validated free 720p item, and then uses the existing verification path. Pull failures use fixed reason codes. Feed search requires exactly one matching batch and narrated prompts try sentence-opening phrases. Logging redacts HTTP and blob URLs; no path presses play.
- `tests/test_flow_shoot.py`: fake-based tests for editor navigation, menu failures, verification, sanitized logs, unique-batch search, and narrated-shot fallback. The new 720p test raises on the base tile fetch (`card.evaluate`).
- `tests/fixtures/flow_narrated_prompts.md`: three representative narrated prompts containing the supplied working phrases for shots 2, 11, and 38.

## Tests

- `git diff --check`: passed (Git only warned about future CRLF conversion).
- `python -m pytest tests/test_flow_shoot.py`: attempted; `python` is unavailable on this Windows worker.
- Two sibling virtual environment `python.exe` launchers were tried with `-m pytest tests/test_flow_shoot.py`; both fail because their base Python 3.11 executable is missing.
- Confirmed with `git show 4c3c608f:tools/flow_shoot.py` that the base implementation calls `card.evaluate` in `pull_original`, which the new 720p test explicitly rejects.

## Not checked / risk

- No live Flow pull was run; PH#3f2 will run the zero-credit live pull after merge.
- The exact prompts in `/opt/MoonieXHQ/Work/filmformula-m4-looktest/in/sheet_final.md` were unavailable in this Windows worktree. The fixture uses representative prompts from the three supplied phrases; it should be replaced with the exact prompts when available.
- Pytest could not execute without a working Python installation. Fake-based test behavior remains unverified on this worker.
