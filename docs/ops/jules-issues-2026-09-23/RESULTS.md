# Jules on real GitHub issues — 2026-09-23 (CTO a29c7576)

Follow-up to the A/B test (`docs/ops/jules-ab-2026-09-23/`): after the issue
clean-up (180 → ~16 open), every remaining bug was fact-checked on current main
and either briefed to Jules with the 8-line brief, fixed by the CTO, or held
with a reason. Ledgers: `state/jules/iss1.jsonl`, `state/jules/iss2.jsonl`.

| Brief | Issue | Jules session | Outcome |
|---|---|---|---|
| J1 | Agents-Wikis #4 — INDEX link | 6441714361647794265 | merged (Wikis #7, 381e3942) |
| J2 | Agents-Core #73 — self_repo_guard `rm -f` / `touch` | 167589877030705341 | merged (#168, 517e5fa2) |
| J3 | Agents-Core #70 — tmux send_keys settle + rescue Enter | 12083418538388182201 | merged (#168, 517e5fa2) |
| J4 | MoonieX-WebApp #74 item 1 — scene events before boot | 6872009369530616467 | PR #100 verified locally (tsc 0, vitest 460/460, new test fails with the fix removed); CI gives no verdict (billing block: every job failed in 2–4 s, Vercel "Account is blocked"). **Held for the CEO's per-repo OK** — WebApp is `prod_adjacent` and the base branch ships to production. |
| J5 | Agents-Core #58 — ilag_mirror `where` never checked | 6789731670668793802 | PR #171. Review added a no-network test guard: with the check removed, the tests had fallen through to a real Drive call. |

**Not sent to Jules, and why**

| Issue | Decision |
|---|---|
| #158 part 3 — reopen on a live worker marked `failed` | Fixed by the CTO directly (#170, e47dfefb): `tools/delegate.py` changed 9× in 3 days (hot-file hold, jules-ops §1), and the fix was already fully verified. Part 2 not reproduced (drain deletes letters, so an empty inbox is the success state). #158 closed. |
| #83 — delegate SUCCESS before verify / missing worktree / tab reuse | Hot file + design calls (recreating a worktree must not `branch -D` unmerged work). Current facts posted on the issue (comment 5798165520). |
| #124 — C-levels outside tmux unreachable by relay | Design decision (refuse vs. write the letter anyway); only for sessions started by hand. Kept open. |
| #160 — finish-task .cmd kills Windows Terminal | Needs Windows to reproduce; `spawn-worker.ps1` changed 3× in 3 days. Kept open. |
| #161 — worker dies at Claude's folder-trust prompt | HQ-migration CTO's lane; mitigated by the dev-spawn-protocol rule (233e79ab). Code fix touches hot files (`worker_init.py`, `delegate.py`). |
| ClaudeFlow #147, #148 | Root causes fixed in code; closed. Leftovers belong to the parked posting pipeline → LungNote note fac067e8. |
| #165 | Already fixed and closed by CTO 0e8d80b8 (69721509). |
