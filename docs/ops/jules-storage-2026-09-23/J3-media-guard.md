Context: one Agents-Core worktree is 867 MB, 738 MB of it media committed under `docs/`. `config/storage-policy.yaml` → `media_guard` says: no new media file larger than `max_bytes` may be added to git unless its path matches `allow`. Build the guard as a standalone script (it gets wired into git hooks later by someone else — do not wire it).

1. GOAL — the command that must pass: `python -m pytest scripts/test_media_guard.py -q` exits 0.
2. FILES you may touch: `scripts/media_guard.py` (new), `scripts/test_media_guard.py` (new). No other file. Do not edit `config/storage-policy.yaml`, `scripts/install-git-hooks.sh`, `.githooks/`, or `pytest.ini`.
3. FORBIDDEN: scratch/log/patch files anywhere, dependency or lockfile edits (pyyaml is already in requirements.txt), editing any existing test, skipping or loosening a test, network calls, anything outside tmp_path in tests.
4. SPEC:
   - `python scripts/media_guard.py [--policy PATH] [--repo DIR]` checks the STAGED changes of the repo (default cwd): files added or modified in the index (`git diff --cached --name-only --diff-filter=AM -z`). For each whose extension (case-insensitive) is in `media_guard.extensions`, read its staged size with `git cat-file -s :<path>`; if size > `max_bytes` and the path matches none of `media_guard.allow` (fnmatch, `**` any depth), it is a violation.
   - Exit 0 and print nothing when clean. Exit 1 when any violation, printing one line per file: `media_guard: <path> <size in MB, 1 decimal> MB > <limit> MB — keep media out of git (ADR 0030); put it in the task's out/ folder or Drive`.
   - `--policy` default: `config/storage-policy.yaml` resolved relative to the script's repo root (`Path(__file__).resolve().parent.parent`), so it works from any cwd.
   - Paths with spaces and non-ASCII (Thai) names must work (hence `-z`).
   - Tests build a throwaway repo in tmp_path (`git init`, set user.name/email locally) and a tmp policy file: small png passes; 2 MiB mp4 fails with exit 1 and the message; 2 MiB `.MP4` upper-case fails; 2 MiB mp4 under an allowed glob passes; 2 MiB `.txt` passes (not media); a Thai filename with a space fails correctly; a deleted media file is not a violation; a pure `git mv` of an already-committed large media file is not a violation (renames are excluded by `--diff-filter=AM`; run with `--no-renames` off, i.e. default rename detection).
5. ENV NOTE: tests need `git` on PATH; if your VM lacks something the repo already declares, report it — do not add dependencies.
6. DELIVERABLE: one PR titled `storage: media guard for staged files (ADR 0030 J3)`; description = behaviour + the exact test command output.
7. FACTS, NOT GUESSES: every claim in the PR body cites the command output or file:line that proves it; anything you could not establish is written as "unknown — not verified", never guessed. State in the PR body which model you are running as, or "unknown" if you cannot tell.
8. No questions needed; proceed.
