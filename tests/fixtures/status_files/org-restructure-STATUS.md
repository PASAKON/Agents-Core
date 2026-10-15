# OrgRestructure — STATUS (Project Head (CTO) #7cf528f0, owner CTO Main cto-c34459eb)

Brief: Contabo `state/ph-briefs/project_head-7cf528f0.md` (2026-10-14). Host contabo, budget $0.
Goal: close out org restructure P2 after the move to one CTO Main + one CMO Main, fix the gaps the
move found, ship the CEO's session-name/persona and CMO-model orders. Each milestone = a pushed
feature branch with tests; CTO Main lands it, the PH never merges.

% = milestones with evidence ÷ 15 (M7–M13, M10c and P3-A added by CTO Main orders on 14 Oct). Landed 10/15 = 67%.

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
| M11 | Escalation watch (CEO order 14 Oct ~11:45 TH) | PR ready (round-2 Codex review task-7f12fc4f fixed by task-6603d0c2; B-1 fixed on main by #309), merge on hold | PR #292 @60010200, CI green, 44 escalation tests; its Run card (sha-pinned, install the service + timer) is in the PR body |
| M12 | winbox runners: no task text through shell argv parsing | landed | PR #293 @c9b8e3b1, merge 698bb894; winbox self-test 8/8 PASS |
| M13 | A Project Head on the Mac and winbox (CEO 14 Oct 13:00 TH via COO): a Mac local, b Contabo→Mac card, c winbox | a landed; b, c(3) PRs open; c(2) blocked | PR #287 merge 598144d9 (a); PR #290 @5b3276c7 (b); PR #282 @0a03806a (c3); docs/ops/ph-anywhere.md has the install bytes |
| M10d | Every live session carries its host emoji: the rename service sweeps sessions that lack only it (CEO 15 Oct ~04:25 TH, brief state/handoff/2026-10-15/brief-7cf-names-sweep.md) | PR ready, merge on hold | PR #323 @2fa20adf (task-0a025bd6): 170 tests; a read-only sweep on Contabo queued exactly the 7 names in the brief; deploy = Run card restart of rename-service.service (tmux is in org-tmux.scope, not that unit) |
| S1 | Session Steward step 1: the watchdog reaps finished workers on Linux (the reap and the sweep were darwin-only) | PR ready, merge on hold | PR #318 @07fba881 (task-e366b1e0): 135 tests; closes only on an idle pane; deploy = Run card restart of mooniex-watchdog.service (tmux not in its cgroup) |
| B2 | Brief item 2: fyi/report never wake a C-level box | PR ready, merge on hold | PR #322 @afdf27f0 (task-762b6bd2): 938 passed / 1 skipped; no deploy |
| B5 | Brief item 5: sparse worktrees on every spawn path | PR ready, merge on hold | PR #324 @d8a27223 (task-49b623ed): the cause was scripts/spawn-worker-remote.sh:296 + restore_worktree doing a full add (~985 MB vs 225 MB sparse); 258 passed |
| QG | PH hands-on flag + runner-share line (quota guard, rework after §2b task-3f66c29c) | PR ready, merge on hold | PR #313 @1209b9af: 37 tests; the merge sha goes to CTO Main for the COO |
| TH | Thai→English batches (COO item 4/5, due 18 Oct) | 2 PRs ready, merge on hold; B01–B05 not yet re-created | PR #315 (task-234108f6, 1 file); PR #316 (task-b19d57dd, CEO-facing Thai in session-worktree restored by PH fix 1e2eacff) |
| M6 | Close-out with Skill learning | open | — |

Blocker: M13c(2) #238, the winbox org_dispatch key. Committing its installer was refused by the classifier
[Unauthorized Persistence] (14 Oct); waiting on the CEO, via CTO Main, since 14 Oct 08:20 (Contabo clock).
Winbox delegation stays paused until M12 lands and a first live spawn checks the claude TUI.

Worker job: LungNote 09d85a20 phase 1 (log-only ORG_IDENTITY_STRICT), task-afe57b21: PR #269, CTO lands it after #268.


Follow-up (CTO order 14 Oct): `state/` sticky bit + `state/locks` g-w. Landed as PR #297 (merge b0444500),
docs/ops/state-dir-perms.md; card RUN-20261014-0753-cc86 ran (exit 0): state = drwxrwsr-t, state/locks =
drwxr-sr-x. Secretary permission errors: 0 at 14:57 TH; the 24 h check is due 15 Oct 15:00 TH.

Merge hold (14 Oct, after #309 merged as e8ceb77b): the auto-mode classifier refused my next PH merge as
[Merge Without Review]. Every PR above waits on the user's ruling; no further PH merge until then.

Decided for CEO: none yet.

Routed, not done by this PH: security item LungNote 09d85a20 (fix proposal to CTO Main); ADR 0009
PH row in Agents-Rules (Mac-only, reminder only).

Learning for close-out: `scripts/test_model_routing_consistency.py` is a script (`main()`, no `test_*`), so
passing it to pytest runs nothing; M3 broke it and CTO Main fixed it in PR #258. Run it with python directly.

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
