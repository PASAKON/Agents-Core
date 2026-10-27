# task-f5c77da6 — RunMedia M7: close the stage_one TOCTOU

## Summary
`stage_one` now copies the bytes of the fd it opened into a private file in the work dir and sniffs, probes and converts
that copy only; the original path is never opened a second time, so a swap after the open can no longer reach ffprobe or
ffmpeg. The copy is size-capped, needs free disk, and is deleted on success and on every refusal. The branch is committed
locally; **no PR is open yet** (see Issues / Blockers).

## What changed (`tools/ask_run.py`)
- `_copy_capped` now creates its target `O_EXCL`, mode `0600` (nothing already at that name is followed or overwritten).
- New `_stage_source(fd, size, copy, kind, refuse)`: refuses a source over `MAX_SOURCE_BYTES` (`too_large … as a source`,
  same wording and video hint as before), checks `shutil.disk_usage(work_dir).free >= size + STAGE_DISK_MARGIN`
  (else `no_space`, which names `TMPDIR`), copies, re-checks the cap on what was actually read (the file may grow), and
  turns an `OSError` during the copy into an `invalid_media` refusal instead of a traceback.
- `stage_one`: still sniffs the first 64 bytes from the open fd, but only to refuse a wrong type before spending a copy and
  to know the kind. After the copy it sniffs the copy (same `changed while it was being read; try again` message on a
  mismatch), runs `_probe` and `_convert_args` on `<work_dir>/<index>.src`, and for an as-is item `os.replace`s the copy
  to its final name, so the bytes that were probed are the bytes uploaded. `finally` closes the fd and unlinks the copy.
- `_too_large` takes an optional `cap` (default unchanged).
- New constants, with the reason in a comment: `MAX_SOURCE_BYTES = 2048 MB`, `STAGE_DISK_MARGIN = 128 MB`.
- Header comment and `docs/design/run-inbox/QUESTIONS.md` §11 (Shrink before upload) say the source is copied first.

## Tests (`tests/test_ask_run_media.py`)
Harness: `put()` remembers the name each file was written under, and `FakeTools` finds a scripted ffprobe answer by the
bytes of the file it is handed (the tools now get `0.src`, not the test's file name) and records every `-i` input with
its bytes at call time. The 11 existing `tools.probe[name]` lines are unchanged.

New (20): (a) swap after `_open_regular`, symlink to a text file and another picture, each as-is and shrunk — the tools
only ever get `<work>/0.src` holding the original bytes, never the original path, and the staged sha equals the original;
(b) oversize refuses before any copy (image, video + hint), exactly-at-cap passes, growth past the cap during the copy
refuses; (c) low disk refuses on both sides of the boundary, asks `disk_usage` about the work dir, and through the CLI
sends nothing and leaves no temp dir; (d) no `*.src` left after success (as-is and shrunk), after four kinds of refusal
(ffprobe fails, ffmpeg fails, picture unmeasurable, over its cap as it is), after a tool raising, after a failed copy;
plus 0600 + O_EXCL (a planted symlink at the name is not written through) and the copy-no-longer-sniffs refusal.

Proved to bite: against the unfixed `tools/ask_run.py` the new tests fail (18 of 20; the 4 swap tests fail because the tool
is handed `…/cover.png` instead of `…/0.src`). Reverting only the convert path, only the probe path, only the unlink, or
only the disk check each fails its own tests (2, 4, 8, 2 failures) and the file was restored byte-identical.

## Evidence
```
python -m pytest tests/test_ask_run_media.py tests/test_ask_run_questions.py
baseline (before change): 508 passed
after:                    528 passed, 0 failed, 0 skipped   (real-ffmpeg end-to-end test ran, ffmpeg is installed)
```
Wider run of every test file that mentions `ask_run` (18 files): 1696 passed, 20 failed, 1 xfailed. The 20 failures are in
`test_email_ceo.py` (13), `test_spend_cap_flags.py` (5), `test_coo_gate.py` (1), `test_ph_on_mac.py` (1) and are
**identical with the HEAD `ask_run.py`** (same 20 FAILED ids, 364 passed in both runs), so they are not from this change.

## Not checked / risk
- No PR was opened: Hard Rule 2 forbids a worker `git push`, the brief asks for a PR. Branch `agent/developer-task-f5c77da6`
  is committed locally and not pushed; nothing was merged and the worktree was not removed.
- `MAX_SOURCE_BYTES` (2 GiB) and `STAGE_DISK_MARGIN` (128 MB) are my judgment, not measured on a real card. A legitimate
  source between 2 GiB and the old unbounded size is now refused with a "cut it down" message; one near the cap costs a
  full sequential copy (seconds) before ffprobe runs.
- Existing staging tests use the real `shutil.disk_usage`, so on a box with under ~128 MB free in the temp dir they fail
  by design (`no_space`) rather than pass.
- Not exercised: a real concurrent swap against real ffprobe/ffmpeg (the race is simulated with a patched
  `_open_regular`); Windows (winbox) `O_EXCL`/`os.replace` semantics, which are standard but untested here; the
  `ask_run` MCP path beyond the existing `test_mcp_media_*` tests, which pass.
- The `org:` wiki tool answered "not available" here, so I skimmed `/opt/MoonieXHQ/Agents/Rules/IRON-RULES.md` by keyword
  only and did not read `playbooks/developer.md` or the project page; nothing in what I saw conflicts with the change.
- Left alone: untracked `state/ph-briefs/` appeared in the worktree during the task and is not mine; it is not committed.
