# PR #612 second-session review

Verdict: **approve**. No blocking defect found in the requested boot recovery changes. One documentation nit below.

Reviewed `git diff origin/main...origin/agent/codex-task-1f4497f0`, PR tip `7bc3154b55e0f14bc3392252da1ef97da70281f2`. Local HEAD was `63d0f01e35cd9468f83631679b7485e449cc5db0`; line references below refer to the PR version.

## Findings

- Non-blocking documentation nit — `docs/reports/task-1f4497f0/REPORT.md:51`: the risk section still describes a 15-minute service timeout and only two remaining minutes. `deploy/systemd/org-resume.service:16` now sets 30 minutes. Update that historical validation note to avoid misleading rollout reviewers.
- `scripts/org-resume.sh:13`: readiness executes `psycopg.connect` directly and `SELECT 1`, with a three-second connection timeout and eight-second outer command timeout. It cannot use `lib.db`'s snapshot fallback. Both output streams of the complete wrapper invocation are discarded; failure messages contain no URL. Exhaustion returns 1 after the 600-second deadline (plus a polling/probe overrun).
- `scripts/org-resume.sh:39`: four total attempts, with three 60-second sleeps; each attempt resets status. Recovery returns zero if the final report succeeds. Exhausted resume failures remain nonzero even when reporting succeeds; report failures also return nonzero (and replace the earlier numeric error code).
- `tools/restart_run.py:885`: existing tmux sessions are skipped before creation or scope manipulation. `tools/restart_run.py:927` archives the manifest and removes the marker only when no entry failed. These unchanged paths support repeating a partial launch without duplicating live panes. Their contents match the reviewed branch in this worktree.
- `scripts/org-postgres-tailnet.sh:6`: IP polling has a 300-second deadline. `scripts/org-postgres-tailnet.sh:25` performs only `docker restart org-postgres`, at most once, followed by ten one-second listener polls. There are no remove/create/volume/network mutations. The Docker command itself relies on the unit's six-minute timeout for its bound.
- `deploy/systemd/org-postgres-tailnet.service:3`: After/Wants includes Docker and tailscaled; its timeout is six minutes at line 9. `deploy/systemd/org-resume.service:4` wants and follows the helper, with a 30-minute timeout at line 16. Wants intentionally allows resume to run after helper failure, where the independent database probe still gates recovery.
- `tests/test_org_resume_boot.py:45`: tests execute the shell scripts, including the actual inline Python probe against a failing psycopg stub, rather than merely asserting source strings. Retry and listener cases exercise command counts and exit statuses. They are useful behavioral unit tests, subject to the limitations below.

## Validation

- Ran `python3 -m unittest discover -s tests -p test_org_resume_boot.py -v`: **10 passed, zero skips**.
- Because HEAD does not contain the PR, extracted the seven required script/unit/test files verbatim with `git show` into a temporary directory inside this assigned worktree, ran the suite there, and removed that temporary directory automatically. No checkout or tracked code modification was made.
- The suite included shell syntax checks and isolated `systemd-analyze verify` with dummy Docker/tailscaled units. No services were started.
- `git diff origin/main...origin/agent/codex-task-1f4497f0 --check` passed.

## Not checked / risk

- No live Postgres, Docker, Tailscale, tmux recovery, secrets retrieval, notification, or reboot was exercised. Nothing was installed, enabled, pushed, or merged. Host rollout remains necessary to verify recovery from Docker's failed bind state.
- `tests/test_org_resume_boot.py:45` uses an empty SQLite file and a psycopg stub; it does not reproduce a usable snapshot fallback or assert that the stub was reached. A setup/import failure could also satisfy its failure assertions. Static inspection independently establishes the direct probe and redirection.
- Retry tests stub `restart_run.py`; they do not test manifest retention themselves. Existing idempotence/partial-failure tests were inspected in `tests/test_restart_run.py` and `tests/test_restart_resume_gaps.py`, but not executed in this review.
- Existing behavior at `tools/restart_run.py:885` treats pane existence as recovery. If an earlier attempt created a pane but failed waiting for empty input or sending the resume message (lines 918–922), a retry can skip that pane and clear the pending manifest. This avoids duplicate sessions but does not guarantee message delivery or application health.
- The helper checks an exact IPv4 socket, not database health. Its standalone Docker invocation has no command timeout; the six-minute bound applies under its systemd unit. Polling deadlines may overrun by a probe/sleep interval.
- Thirty minutes is an overall service ceiling, not a guarantee all four attempts finish: individual session waits default to 600 seconds. Existing `KillMode=process` also means service timeout is not a guarantee every descendant stops. No timeout/kill integration test was performed.
