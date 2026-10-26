# REPORT task-0b13358b

Reviewed `git diff origin/main...origin/agent/codex-task-51c9f440`, head `5f58864380bcfb0f55d951f1d5e5045d2b67cba2` (PR #451). Implementation files were not edited; no commits were made.

## Findings

- **P1 — Partial prep failure in reboot mode leaves saved sessions down.** `scripts/org-restart.sh:48` limits recovery to `--sessions-only`. Run the default reboot command with two sessions: the first saves and closes successfully, while the second fails (for example, its input contains a draft). Prep returns 1 with a new recovery marker, but the wrapper skips resume and exits without scheduling a reboot. The first session remains down until manual intervention. The changed-marker safeguard should also protect rollback in reboot mode. This mode restriction predates this PR, but remains a blocker against the brief's explicit recovery goal. Reproduced with the head's `_shell(..., fail='prep', prep_marker=True)` helper without `--sessions-only`: exit 4, only a prep call, no resume or reboot. `tests/test_restart_run.py:506` covers partial failure only in sessions mode and misses this case.

- **P2 — Naive timestamps prevent stale-state retirement with an uncaught exception.** `tools/restart_run.py:258-261` parses an ISO timestamp without checking its timezone, then subtracts it from an aware UTC datetime. A marker containing a timezone-less ISO timestamp from seven hours ago causes `TypeError: can't subtract offset-naive and offset-aware datetimes`, in both real and dry-run prep. Repeated attempts cannot retire that stale state. Define handling for naive timestamps (normalization only if its timezone is known, otherwise an actionable controlled refusal). This is a robustness issue for externally supplied/legacy state; this repository's normal writer emits aware timestamps. The new age tests exercise only aware timestamps.

## Other reviewed behavior

- Valid aware timestamps, including timezone offsets, support subtraction correctly. Manifest-only state uses an aware UTC mtime. Exactly six hours remains protected; strictly older state is retired. Dry-run retirement only prints intent and preserves files, as verified by the tests.
- A marker missing `timestamp` raises uncaught `KeyError`; malformed JSON raises `JSONDecodeError` (caught by the CLI's `ValueError` handler). Neither changes the recovery marker or manifest or closes sessions. The unchanged-marker check therefore prevents fallback replay in sessions mode. These are fail-closed cases, although missing-field diagnostics should be improved alongside timestamp validation. No mtime fallback is attempted for invalid marker JSON.
- The shell quotes marker paths and comparisons correctly. The initial `cat ... || true`, prep in an `if`, and fallback `resume || true` avoid unwanted `set -e` termination; the original prep status is preserved. No new pipefail issue was found. Command substitution strips trailing newlines, so the comparison is not literally byte-for-byte, but the normal marker writer changes its timestamp content; no normal-path failure was demonstrated from this distinction.
- The tests cover stale/fresh state, marker absence, dry-run preservation, unchanged old markers, and replacement markers. Shell tests stub prep/resume, so passing them does not establish end-to-end recovery or timestamp parsing coverage.

## Validation performed

- Ran `pytest tests/test_restart_run.py tests/test_restart_resume_gaps.py tests/test_restart_plan.py -q` on an exact `git archive` of the requested head within the assigned worktree, using `/opt/MoonieXHQ/Agents/Core/.venv/bin` on PATH: **118 passed, exit 0**. Pytest emitted cleanup warnings about pre-existing temporary directories being nonempty.
- Executed isolated, in-memory review probes using the head's test helpers: reproduced default-mode missing rollback, naive timestamp TypeError, missing timestamp KeyError, and malformed JSON rejection. All marker-error probes preserved the marker and manifest. No real sessions or services were operated.
- Read the requested diff and surrounding prep/resume/CLI and shell code. No MAILBOX.md was present when checked.

## Files changed

- Only `docs/reports/task-0b13358b/REPORT.md` is retained as a new file. The temporary head archive used for validation was removed.

## Blockers

- Direct checkout of the requested head was blocked because the worktree's Git metadata is read-only (`index.lock` creation failed). The original worktree HEAD remains `f88af2edbae8b81258d2f112155c9008e49645ff`; tests instead ran against the exact requested-head archive inside this worktree. No approval or repository modification was needed for this fallback.
- No remaining blocker to this review. Live restart behavior was assessed through code and isolated mocks, not a production reboot.

## Skill learning

- (none)
