# REPORT task-53711e45

## Summary
Added cap-checked Run SCRIPT card support for the CMO's two paid fal workflows:
1. Extended `tools/fal_tts.py` with `bytedance/seed-audio-1.0` (`SEED`), taking a local `reference_audio` (`.mp3` or `.wav` under `/opt/MoonieXHQ/Work/`), uploading it once per run to fal storage only (`https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3` -> `https://v3.fal.media/` / `https://v3b.fal.media/`), and pricing every call before sending at `$0.1875/min` (`$0.003125/s`, read off the fal model page) using a `10 chars/s` speaking-rate floor (`$0.3125 / 1,000 chars`) plus recording any `audio.duration` overrun in `spent` and the ledger.
2. Created `tools/fal_lipsync.py` for `fal-ai/sync-lipsync` (`lipsync-1.9.0-beta` "v1" at `$0.0117/s`; `lipsync-2` at `$0.05/s`) against one `reference_video` (or `video_file`), pricing every call before sending from the duration in seconds of its local input `audio_file` (`.mp3` or `.wav`, parsed in pure stdlib), uploading reference video and input audio to fal storage only, sharing `<job>.ledger.jsonl` across runs, and stopping before `--max-usd` (`EXIT_CAP = 3`) or after 2 HTTP 5xx server errors in a row (`EXIT_FAIL = 1`).
3. Updated `config/spend-tools.txt` with the `bytedance/seed-audio-1.0` comment and the new `tools/fal_lipsync.py --max-usd` entry, and added offline unit tests in `tests/test_fal_tts.py` and `tests/test_fal_lipsync.py`.

## Files changed
- `tools/fal_tts.py` — added `SEED = "bytedance/seed-audio-1.0"`, `PRICES[SEED]` (`$0.3125 / 1,000 chars` from `$0.1875/min` at `10 chars/s`), `UPLOAD_URL`, `STORAGE_HOSTS`, `_ref_audio`, `_seed_call`, `upload()`, duplicate `--max-usd` rejection, lazy reference audio upload to fal storage only, and `extra_usd` overrun accounting when `res["audio"]["duration"]` exceeds the pre-call estimate.
- `tools/fal_lipsync.py` — new stdlib-only spend tool for `fal-ai/sync-lipsync` (`lipsync-1.9.0-beta` at `$0.0117/s`, `lipsync-2` at `$0.05/s`) with `--job`, `--max-usd` (`allow_abbrev=False`, no short alias, no duplicate flag), `--dry-run`, pure-stdlib `.wav`/`.mp3` duration parsing (`audio_seconds`), fal storage upload (`upload`), key handling identical to `tools/fal_tts.py`, shared `.ledger.jsonl` locking/accounting, and 2-server-error stop.
- `config/spend-tools.txt` — updated `tools/fal_tts.py --max-usd` comment for `bytedance/seed-audio-1.0` and added `tools/fal_lipsync.py --max-usd` with its cap/pricing comment.
- `tests/test_fal_tts.py` — added offline tests for `bytedance/seed-audio-1.0` (single reference upload, queue submission, cap stop before upload, `--dry-run`, duration overrun accounting across reruns, job/call validation, `upload()` storage host enforcement and unkeyed `PUT`, duplicate `--max-usd` refusal).
- `tests/test_fal_lipsync.py` — new offline test suite covering `lipsync-1.9.0-beta` and `lipsync-2` pricing and cap stops, shared ledger across reruns, skipping existing output files, 2 server errors in a row stopping the job, 403 stop and key redaction, `--dry-run`, `--max-usd` flag/value validation, `under_work` symlink/path checks, MP3 (ID3v2, Xing VBR, CBR) and WAV (PCM and IEEE float) duration parsing, fal storage upload security, and stdlib-only AST import check.
- `docs/reports/task-53711e45/REPORT.md` — this report.

## Validation performed
- Under the AGY Remote Worker file-only contract (`python`/`pytest` execution is left to the review process), verified all edits and imports statically and checked `git diff` across all modified and created files.
- Reviewer test command to run (offline, no network, no paid calls):
  `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_fal_tts.py tests/test_fal_lipsync.py tests/test_flow_shoot_card.py -k "fal or spend_tools"`
- Zero live API calls or paid calls were made.

## Not checked / risk
- `bytedance/seed-audio-1.0` is billed by fal per output minute (`$0.1875/min` = `$0.003125/s`) rather than per input character. `tools/fal_tts.py` prices each call before sending at a conservative `10 chars/s` floor (`$0.3125 / 1,000 chars`, vs measured `11.4–15 chars/s` and `~$0.28 / 1,000 chars` in `prototypes/mypasakon-voice/RECIPE.md`) and records any `audio.duration` overrun in `spent` and `extra_usd` after the call completes. Worst case on the final admitted call of a job: if Seed Audio invents silence up to its 120 s output ceiling, that single call can bill up to `$0.375` before the next call is stopped.
- `tools/fal_lipsync.py` computes `.mp3` duration by parsing MPEG Layer III frames (and `Xing`/`Info` VBR frame headers) and `.wav` duration via `wave` / RIFF chunks in pure stdlib. An MP3 with non-standard trailing junk or corrupt mid-stream frame headers stops frame walking at the first invalid header (or raises `JobError` if no valid frame precedes it).
- Storage uploads initiate via `https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3` (which is not Vercel-challenged from Contabo, unlike `api.fal.ai` / `fal.ai`) and require both `upload_url` and `file_url` to start with `https://v3.fal.media/`, `https://v3b.fal.media/`, or `https://fal.media/`. Live end-to-end upload against `rest.alpha.fal.ai` was not executed in this offline worker run.
- Pytest execution was not run in the AGY print-mode shell per the AGY Remote Worker Contract (which forbids `python`/`pytest` commands in print mode); the reviewer should run the pytest command above before merge.

## Blockers
- Per the AGY Remote Worker Contract, no `gh` CLI or org messaging tools are available in this worker environment. After the launcher commits and pushes branch `agent/agy-task-53711e45`, please open the PR to `main`, ask **CTO Main** for review per the `config/spend-tools.txt` header, and report the PR number to the CMO.

## Skill learning
- (none)
