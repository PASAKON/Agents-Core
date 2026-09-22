Context: you are on branch `feature/media-guard-941641718597106202` (PR #163, `scripts/media_guard.py` + `scripts/test_media_guard.py`). Review REJECTED it for the defects below, each reproduced on the target Mac. Fix exactly these; keep everything else as is.

1. GOAL — the command that must pass: `python -m pytest scripts/test_media_guard.py -q` exits 0, AND it still exits 0 when run as `env PATH=/usr/bin:/bin <that same interpreter's absolute path> -m pytest scripts/test_media_guard.py -q` (a machine with no `python` on PATH).
2. FILES you may touch: `scripts/media_guard.py`, `scripts/test_media_guard.py`. No other file.
3. FORBIDDEN: scratch/log/patch files anywhere, dependency or lockfile edits, editing any other test, skipping or loosening an assertion, network calls, anything outside tmp_path in tests.
4. WHY REJECTED (fix each):
   a. `run_guard` calls `["python", ...]`. On the target Mac `python` is not on PATH → `FileNotFoundError: [Errno 2] No such file or directory: 'python'` (measured). Use `sys.executable`.
   b. `git diff --cached --name-only --diff-filter=AM -z` relies on the user's `diff.renames` setting. Measured: with `git config diff.renames false`, a pure `git mv a.mp4 b.mp4` of a committed 2 MB file lists `b.mp4` as added → false violation. Pass `-M` explicitly. Add a test that sets `diff.renames false` in the tmp repo and asserts a pure `git mv` of a committed large mp4 exits 0 — and confirm that test FAILS without `-M` before you add it (say so in the PR body with the output).
   c. All cases live in one test function, so the first failure hides the rest. Split into one test function per case (small png, 2 MiB mp4, `.MP4`, allowed glob, `.txt`, Thai name with a space, deleted file, git mv default, git mv with `diff.renames false`), sharing a fixture that builds the tmp repo + policy.
   d. The PR body stated "Model running as: Claude 3.5 Sonnet". That is a guess, not a fact. Do NOT state a model at all.
   e. Add a one-paragraph module docstring to `scripts/media_guard.py` (what it checks, exit codes, ADR 0030).
5. ENV NOTE: tests need `git` on PATH. If your VM lacks something the repo already declares, report it — do not add dependencies.
6. DELIVERABLE: one PR titled `storage: media guard for staged files (ADR 0030 J3, fixes)`; body = one line per item a–e saying what changed + the exact output of BOTH goal commands.
7. FACTS, NOT GUESSES: every claim in the PR body cites the command output or file:line that proves it; anything you could not establish is written as "unknown — not verified", never guessed.
8. No questions needed; proceed.
