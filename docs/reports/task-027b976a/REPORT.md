# REPORT task-027b976a

## Result

Implemented a shared project-page original pull for `run` and `pull`. No live Flow access, browser access, Generate action, or credit spend occurred. The launcher owns committing and pushing.

## Cause

Generation `--resolution 720p` and export `--download-resolution` are separate settings; export defaults to 1080p. The old card path clicked the card, assumed it would reach `/edit/`, and attempted an editor download. A canceled save (or failed route wait) fell through to the legacy upscale method without establishing the editor route. That method explicitly rejects project-page URLs. The original fetch used `page.request.get`, not the page's session-backed JavaScript fetch, and was unavailable as a fallback for default exports. `pull` also returned zero regardless of verification failures.

The supplied incident establishes Chromium's `Download.save_as: canceled` symptom. Offline inspection cannot establish why Chromium canceled that individual download; this change bypasses that mechanism for originals.

## Files changed

- `tools/flow_shoot.py`: fetch the matched tile's video source with in-page `fetch(..., {credentials: 'include'})`; return encoded bytes and a sanitized clip ID, never the source URL. Save into the output directory and use `verify_clip` for duration, audio, and aspect-specific dimensions. Verify originals at 1280x720 or 720x1280. Navigate to the clip editor before optional free 1080p export. Verify that export separately and replace the original atomically only on success; otherwise retain the verified original and log one line. Both commands share this path. Failed pull verification now exits 1. Project-feed completion cannot be triggered by an unrelated page-wide video. Removed a signed URL from the legacy HTTP error.
- `tools/flow_shoot_card.py`: summary counts only verified ledger rows whose file and SHA-256 match an output actually received and checked locally.
- `tests/test_flow_shoot.py`: fake-browser run/pull coverage for both aspect ratios, both export targets, canceled upscale downloads, wrong dimensions/duration, original retention, valid/invalid upgrades, and interrupted replacement copying. Probe fakes inspect the saved file; `verify_clip` remains the real verifier in the run/pull regressions. Existing suite also exercises real ffmpeg/ffprobe fixtures.
- `tests/test_flow_shoot_card.py`: count verified received files; exclude rejected or absent files.
- This report.

## Validation performed

Base revision: `3e7d1392`. Loaded `git show HEAD:tools/flow_shoot.py` into the imported module in a separate Python process, then ran the new canceled-download regression without replacing working files:

```text
tests/test_flow_shoot.py::test_original_pull_file_verification[1080p-16:9-None-run]
1 failed in 0.97s
```

The base returned 1 instead of the required 0 after the fake editor raised `Download.save_as: canceled`. All submits in these tests are fake methods, not browser actions.

Final required command:

```text
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_flow_shoot.py tests/test_flow_shoot_card.py tests/test_spend_cap_flags.py
295 passed in 16.67s
```

`git diff --check` passed. No `-q` was added. MAILBOX.md was absent at checks.

## Not checked / risk

Only PH#3f2's post-merge live pull can prove that the current ILAG Lituya project tiles expose their original video source, the page session permits fetching those bytes (including any CORS behavior), search selects the intended historical clips, and the three actual files pass ffprobe at 1280x720 and 8 seconds. The fakes do not execute browser JavaScript or prove the current Flow DOM. The clip editor ID is taken from an editor link when available, otherwise the video's path; its correspondence to the live editor route and the optional upscale menu remain unverified. Failure there preserves the original.

For the planned zero-credit recovery, use `flow_shoot pull` with the existing sheet and ledger, `--only 2,11,38 --aspect 16:9 --download-resolution 720p`, and the intended output directory. This bypasses editor downloads and upscale entirely. Existing runner filenames remain `shot-02.mp4`, `shot-11.mp4`, and `shot-38.mp4`. No live check was attempted here, including browser Home or running Chrome.

## Blockers

- None for implementation and offline validation. Live confirmation is intentionally deferred until after merge.

## Skill learning

- (none)
