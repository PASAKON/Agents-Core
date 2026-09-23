# Jules A/B 2026-09-23 — running findings

Batch `ab1`: 13 tasks × arm A (7-line brief) / arm B (2-sentence brief) = 26 sessions.
Ledger `state/jules/ab1.jsonl`; briefs + allowlists in `briefs/`. Final table goes in REPORT.md.

## 2026-09-23 06:40–06:50 — first merges, and what closing a PR does

- **Merged (A arm):** MoonieX-Scriptable #2 (T09-A, 4 files, 10 tests; 21/21 with the
  repo's other tests on current main) → `1fdcb636`; Agents-Wikis #6 (T10-A, stdlib link
  checker, 26 broken links reported, exit 1 as specified) → `2737bf99`.
- **Closed as superseded (B arm):** Scriptable #1 (half the scope, test file inside
  `server/`), Agents-Wikis #5 (committed its own output `broken_links.txt`).
- **A-arm defect caught at review:** #2's `pytest.ini` (`testpaths = tests`) silently
  dropped 11 existing tests from a plain `pytest`. Gate scripts check *which files* a PR
  touches, not *what a config change excludes*. Fixed after merge (`30a555b`).
- **Closing a PR restarts its finished session — archiving first does NOT prevent it.**
  Both B sessions were archived via `POST /sessions/{id}:archive` (archived=true), then
  their PRs closed with a comment; both went COMPLETED → IN_PROGRESS within seconds.
  The trigger is the PR comment. With an explicit "Superseded by #N … closed" comment the
  restarted agent answered "acknowledged … I will now stop work" (contrast CTO 0e8d80b8's
  case, where a restarted run edited requirements.txt). Rule candidate: close
  superseded Jules PRs with a one-line *superseded — stop* comment, then verify no new
  branch/PR appears.
- **Repo naming trap:** the local folder `~/Projects/Agents-Wikis` is a clone of
  `PASAKON/Agents-Rules`; `PASAKON/Agents-Wikis` is `~/MoonieXHQ/Agents/Wikis` (= old
  `~/Projects/LLMs`). Resolve a PR's repo with `git remote get-url`, never by folder name.
- **…and the restarted session does not end.** 150 s after the close both restarted B
  sessions were still `IN_PROGRESS` with no new activity (18 activities, updateTime
  ticking) and had pushed nothing (each repo: branches `main` only, 0 open PRs). The
  agent *says* it stops; the session state does not follow. Open question: does such a
  zombie hold a concurrency slot? Recheck at batch review; if still IN_PROGRESS, test
  `DELETE /sessions/{id}`.
