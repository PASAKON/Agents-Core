# OrgRestructure — STATUS (Project Head (CTO) #7cf528f0, owner CTO Main cto-c34459eb)

Brief: Contabo `state/ph-briefs/project_head-7cf528f0.md` (2026-10-14). Host contabo, budget $0.
Goal: close out org restructure P2 after the move to one CTO Main + one CMO Main, fix the gaps the
move found, ship the CEO's session-name/persona and CMO-model orders. Each milestone = a pushed
feature branch with tests; CTO Main lands it, the PH never merges.

% = milestones with evidence ÷ 6.

| # | Milestone | State | Evidence |
|---|---|---|---|
| M1 | live-sessions prints PH rows by default, "+N workers" counts real workers | landed | 0bba6e15, on origin/main via PR #255 (CTO Main) |
| M2 | P2 doc: status line, ORG_SESSION_SCOPE evidence, "Starting a Project Head" lesson | landed | a5e969a4, on origin/main via PR #255 |
| M3 | Session names `<HOST> <ROLE> (<Name>) #<id>` + `_NAME_RE` (persona text landed in 975c2ebb by CTO Main) | landed | 4e69c207 via PR #258 = 2bd6e650 (with C-level effort medium); live Core 4c6d62b7 |
| M4 | CMO model → Opus 5.5 xhigh (Q-20261014-0227-c918) | landed | eb6c3fa4, merge 626d60fe |
| M5 | P3 plan incl. Project Monitor backend (plan only, to CTO Main before building) | pushed, waiting go | branch `ph-7cf528f0/p3-plan`, docs/plans/org-restructure-p3-plan.md |
| M6 | Close-out with Skill learning | open | — |

Blocker: none (the dead rows were cancelled by CTO Main 02:54Z).

Worker job: LungNote 09d85a20 phase 1 (log-only ORG_IDENTITY_STRICT), go from CTO Main 02:44Z; task-afe57b21 security_engineer running since 09:54 TH (tmux wd-afe57b21), PH reviews and pushes.


Decided for CEO: none yet.

Routed, not done by this PH: security item LungNote 09d85a20 (fix proposal to CTO Main); ADR 0009
PH row in Agents-Rules (Mac-only, reminder only).

Learning for close-out: `scripts/test_model_routing_consistency.py` is a script (`main()`, no `test_*`), so
passing it to pytest runs nothing; M3 broke it and CTO Main fixed it in PR #258. Run it with python directly.
