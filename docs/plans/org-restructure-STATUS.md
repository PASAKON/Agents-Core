# OrgRestructure — STATUS (Project Head (CTO) #7cf528f0, owner CTO Main cto-c34459eb)

Brief: Contabo `state/ph-briefs/project_head-7cf528f0.md` (2026-10-14). Host contabo, budget $0.
Goal: close out org restructure P2 after the move to one CTO Main + one CMO Main, fix the gaps the
move found, ship the CEO's session-name/persona and CMO-model orders. Each milestone = a pushed
feature branch with tests; CTO Main lands it, the PH never merges.

% = milestones with evidence ÷ 22 (rows added by CTO Main orders on 14–15 Oct). Landed 22/22 = 100%; the registry (`tools/portfolio.py show org-restructure`) agrees. Closed 15 Oct 2026.

| # | Milestone | State | Evidence |
|---|---|---|---|
| M1 | live-sessions prints PH rows by default, "+N workers" counts real workers | landed | 0bba6e15, PR #255 |
| M2 | P2 doc: status line, ORG_SESSION_SCOPE evidence, "Starting a Project Head" lesson | landed | a5e969a4, PR #255 |
| M3 | Session names + `_NAME_RE` | landed | 4e69c207 via PR #258 |
| M4 | CMO model → Opus 5.5 xhigh (Q-20261014-0227-c918) | landed | eb6c3fa4, merge 626d60fe |
| M5 | P3 plan incl. Project Monitor backend | landed | docs/plans/org-restructure-p3-plan.md |
| M7 | Short names (`Dev#<id3> - ` etc.) | landed | PR #263 |
| P3-A | P3 phase A | landed | PR #264 |
| M8 | winbox title + role; node_dispatch args cap 4000; COO `verified` grant | landed; grant = Run card | PR #268, merge d4ff2ae0 |
| M9 | Host emoji in names; session-rename PH topic not doubled | landed | PR #275 |
| M10 | Names enforced in live-sessions (M10a) + rename service over a unix socket, SO_PEERCRED (M10b, #272) | landed | PR #283 @b7150a88, merge 0e0e8d3e (4 §2b rounds); take-back LOW = PR #299; deploy = Run card (rename-service.service), after the live sync |
| M10c | The rename service on the Mac (LaunchDaemon as the sessions' user, not root) | landed; install waits on the CEO | PR #289 @fb0d0780, merge 290f7a3b; CTO Main sends the CEO the sha-pinned sudo line after M10d lands (one install brings the sweep too) |
| M11 | Escalation watch (CEO order 14 Oct ~11:45 TH) | landed; timer live | PR #292 merge a700dad9; escalation-watch.timer enabled on RUN-20261015-0338-0546 (fired 06:16:51 CEST) |
| M12 | winbox runners: no task text through shell argv parsing | landed | PR #293 @c9b8e3b1, merge 698bb894; winbox self-test 8/8 PASS |
| M13 | A Project Head on the Mac and winbox (CEO 14 Oct 13:00 TH via COO): a Mac local, b Contabo→Mac card, c winbox | a, b landed; c split out | PR #287 merge 598144d9 (a); PR #290 merge 0bdfb49d (b); c = PR #282 draft, moved to portfolio project `m13c-card-spawn` (CTO Main 15 Oct) |
| M10d | Every live session carries its host emoji: the rename service sweeps sessions that lack only it (CEO 15 Oct ~04:25 TH, brief state/handoff/2026-10-15/brief-7cf-names-sweep.md) | landed; restarted | PRs #323 merge 755caee1 + #335 ad7fe53c; rename-service restarted on RUN-20261015-0338-0546; PH-marker fix #342 merge 7edd92f3 goes live with the Console deploy card restart |
| S1 | Session Steward step 1: the watchdog reaps finished workers on Linux (the reap and the sweep were darwin-only) | landed; restarted | PR #318 merge 14181f9e; mooniex-watchdog restarted on RUN-1348 (active) |
| B2 | Brief item 2: fyi/report never wake a C-level box | landed | PR #322 merge abddc6f4 + kind-parser fix #340 merge bd1cafb2 |
| B5 | Brief item 5: sparse worktrees on every spawn path | landed | PR #324 merge ad25b44b |
| QG | PH hands-on flag + runner-share line (quota guard, rework after §2b task-3f66c29c) | landed | PR #313 merge 26b6ec4a |
| TH | Thai→English batches (COO item 4/5, due 18 Oct) | landed | #315 2bfaa535, #316 ae14b4ba; B01–B05 #326 369a5b4b, #328 2df03000, #329 7d6ea66c; tail #347 2595720c (36 files re-audited, task-72890adb) |
| M10e | live-sessions checker reads the PH marker on the row's own host (Mac PH#671 off-rule; CTO Main 15 Oct) | landed | PR #352 merge c0df4ef7 (task-0a30e4a0, Sonnet) on RUN-20261015-0510-096f; rename-service on #342 code; Mac pulls via PH#671 |
| M6 | Close-out with Skill learning | landed | this PR; journal check below; Skill learning below |

Blocker: none. M13c (winbox PH, #282 draft, conflicts, needs its own §2b; Codex back after the CEO's reset)
is now its own portfolio project `m13c-card-spawn`; the winbox org_dispatch key (#238) waits on the CEO there.
Run Watch (brief state/handoff/2026-10-15/brief-7cf-runwatch-macoff.md) was never one of the 21: portfolio
project `run-watch`, 2/4 (A #327 fbb564f0, B zero-model #330 8578ccab); CTO Main hands it out.

Still open, not mine: PR #269 (LungNote 09d85a20 phase 1, log-only ORG_IDENTITY_STRICT) waits on CTO Main.

Follow-up (CTO order 14 Oct): `state/` sticky bit + `state/locks` g-w. Landed as PR #297 (merge b0444500),
docs/ops/state-dir-perms.md; card RUN-20261014-0753-cc86 ran (exit 0). Secretary permission errors over the
24 h from 14 Oct 07:53 UTC (`journalctl -u mooniex-secretary -u mooniex-secretary-waker | grep -ciE
"permission denied|EPERM|EACCES"`): 0 at 14:03 TH, 15 Oct. That 0 cannot fail: the journal holds no line for
either unit (they log to /home/secretary/runtime/logs/*.log, untouched since their 1 Oct start, no EACCES there
either). Both units active, NRestarts=0 since 1 Oct; state = drwxrwsr-t, state/locks = drwxr-sr-x. No rollback
(`chmod g+w state/locks && chmod -t state` if ever needed). Follow-up for CTO Main: make the units log errors to
the journal, or point the check at their own files.

Merge rule since 26 Oct: the PH merges its own PRs after CTO_Gate_MergeChecklist, one at a time, with no CEO card;
the 08:00 digest lists the merges. A merge the classifier refuses goes to CTO Main as a ready list (PR, head sha,
CI, reviewed), and CTO Main merges it itself (CEO Q-20261026-0814-4870). [SUPERSEDED 2026-10-26] "one Run card per
batch, raised by CTO Main (Q-20261014-2310-6d8b)".

Decided for CEO: none.

Routed, not done by this PH: security item LungNote 09d85a20 (fix proposal to CTO Main); ADR 0009
PH row in Agents-Rules (Mac-only, reminder only); runner bugs (AGY headless "done" with no diff; Codex
re-commits a stale REPORT with no completed turn) to PH SpendGuard with the router fix.

## Skill learning (ADR 0026)

- `scripts/test_model_routing_consistency.py` is a script (`main()`, no `test_*`): pytest on it runs nothing.
  Run it with python directly.
- reopen_task sets the row to pending and does not respawn: delegate_task again. It also prepends the feedback,
  which pushes an `override:` line out of lines 1–5; re-prepend it.
- The MCP create_task drops `runner`; pin with `db.set_fields(runner=…)` plus an `override:` line.
- AGY headless auto-denies every command permission and still reports done with an empty commit. Codex reads
  files through its shell, so never brief it "no commands". Judge a runner by the target-file diff, never
  the row status.
- A Codex round that hits its weekly limit completes no turn; launch.sh re-commits the old REPORT. Check
  `turn.completed` in the transcript before a reopen.
- A worker worktree on Contabo is cut from LOCAL main (~290 unpushed commits, incl. the held a60f1744):
  cherry-pick the worker's own commit onto origin/main; never push its branch as-is (pre-push hook now refuses).
- A sha-pinned card `HEAD = <MERGE_SHA>` never matches Contabo's local main; pin with
  `git merge-base --is-ancestor <sha> HEAD`.
- A duplicate function definition after a merge silently overrides the first (body_kind, #340).
- Stacked PRs need the base merged first (#339 on #336). CI fail-sets can be tests pinning old name shapes.
- A grep count over an empty journal is a check that cannot fail: confirm the unit logs to the journal
  (`journalctl -u X -n 1`) before trusting a 0.
- A live-sync can conflict on generated files (docs/org/SKILL-INDEX.md): regenerate with
  `scripts/skill-curator.py index`, never hand-merge.

## Run cards for CTO Main after landing (copy verbatim; each runs as root on Contabo from the live Core)

None of these restarts an existing unit or touches the tmux server (both new units are tmux clients only).

**M8: org_coo grant on `live_sessions.verified`** (after #268 lands and Core is live-synced). Checked
read-only 14 Oct 06:05Z: the hub has no `verified` column yet, so the card runs `lib.db.init()` first
(forward-only `ALTER … ADD COLUMN`, under the init advisory lock, safe to repeat):
```
cd /opt/MoonieXHQ/Agents/Core && bash scripts/hub/org-python.sh -c "from lib import db; db.init()" && python3 tools/infisical_setup.py run Agents-Core prod --as contabo -- .venv/bin/python deploy/coo-gate/org_coo_role.py --grants-only
```

**M10b: rename service** (after the M10 PR lands and Core is live-synced; `<MERGE_SHA>` = main after it lands):
```
cd /opt/MoonieXHQ/Agents/Core && test "$(git rev-parse HEAD)" = <MERGE_SHA> && git diff --quiet HEAD -- tools lib config policies deploy && install -o root -g root -m 0644 deploy/systemd/rename-service.service /etc/systemd/system/rename-service.service && systemctl daemon-reload && systemctl enable --now rename-service.service && sleep 20 && systemctl --no-pager --lines=10 status rename-service.service
```

**M11: escalation watch**: superseded; the reworked #292 carries its own card.
