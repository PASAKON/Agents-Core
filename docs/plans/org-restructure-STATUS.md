# OrgRestructure — STATUS (Project Head (CTO) #7cf528f0, owner CTO Main cto-c34459eb)

Brief: Contabo `state/ph-briefs/project_head-7cf528f0.md` (2026-10-14). Host contabo, budget $0.
Goal: close out org restructure P2 after the move to one CTO Main + one CMO Main, fix the gaps the
move found, ship the CEO's session-name/persona and CMO-model orders. Each milestone = a pushed
feature branch with tests; CTO Main lands it, the PH never merges.

% = milestones with evidence ÷ 14 (M7–M13 and P3-A added by CTO Main orders on 14 Oct). Landed 9/14 = 64%.

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
| M10 | Names enforced in live-sessions (M10a) + rename request file and root rename service (M10b, #272) | PR open | PR #283; branch `ph-7cf528f0/m10-names-enforced`; deploy = Run card (rename-service.service) |
| M11 | Escalation watch (CEO order 14 Oct ~11:45 TH) | pushed after M10 | branch `ph-7cf528f0/m11-escalation-watch`; deploy = Run card (escalation-watch.timer) |
| M12 | winbox runners: no task text through shell argv parsing | pushed after M11 | branch `ph-7cf528f0/m12-winbox-argv`; winbox self-test 8/8 PASS |
| M13 | A Project Head on the Mac and winbox (CEO 14 Oct 13:00 TH via COO): a Mac local, b Contabo→Mac card, c winbox | a+b PR open; c(3) draft (stacked); c(2) blocked | PR #280 (a+b), PR #282 (c3); docs/ops/ph-anywhere.md has the install bytes |
| M6 | Close-out with Skill learning | open | — |

Blocker: M13c(2) #238, the winbox org_dispatch key. Committing its installer was refused by the classifier
[Unauthorized Persistence] (14 Oct); waiting on the CEO, via CTO Main, since 14 Oct 08:20 (Contabo clock).
Winbox delegation stays paused until M12 lands and a first live spawn checks the claude TUI.

Worker job: LungNote 09d85a20 phase 1 (log-only ORG_IDENTITY_STRICT), task-afe57b21: PR #269, CTO lands it after #268.


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

**M10b: rename service** (after the M10 PR lands and Core is live-synced):
```
cd /opt/MoonieXHQ/Agents/Core && install -m 0644 deploy/systemd/rename-service.service /etc/systemd/system/rename-service.service && systemctl daemon-reload && systemctl enable --now rename-service.service && sleep 20 && systemctl --no-pager --lines=10 status rename-service.service
```

**M11: escalation watch** (after the M11 PR lands and Core is live-synced). It runs once dry first. Its first
`--nudge` pass will mail the COO and the live C-levels about any finding then present (on 14 Oct: "host mac
stopped publishing"):
```
cd /opt/MoonieXHQ/Agents/Core && bash scripts/hub/with-org-db-env.sh .venv/bin/python tools/escalation_watch.py && install -m 0644 deploy/systemd/escalation-watch.service deploy/systemd/escalation-watch.timer /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now escalation-watch.timer && systemctl --no-pager list-timers escalation-watch.timer
```
