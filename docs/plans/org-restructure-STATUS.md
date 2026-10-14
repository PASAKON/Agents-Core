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
| M3 | Session names `<HOST> <ROLE> (<Name>) #<id>` + `_NAME_RE` (persona text landed in 975c2ebb by CTO Main) | pushed | branch `ph-7cf528f0/session-names-persona` 4e69c207 |
| M4 | CMO model → Opus 5.5 xhigh (Q-20261014-0227-c918) | landed | eb6c3fa4, merge 626d60fe |
| M5 | P3 plan incl. Project Monitor backend (plan only, to CTO Main before building) | pushed, waiting go | branch `ph-7cf528f0/p3-plan`, docs/plans/org-restructure-p3-plan.md |
| M6 | Close-out with Skill learning | open | — |

Blocker: none (the dead rows were cancelled by CTO Main 02:54Z).

Worker job: LungNote 09d85a20 phase 1 (log-only ORG_IDENTITY_STRICT), go from CTO Main 02:44Z; task-afe57b21 security_engineer running since 09:54 TH (tmux wd-afe57b21), PH reviews and pushes.

Landing note: CTO Main lands its C-level effort-medium branch first, then M3 4e69c207 on top (CTO Main resolves).

Decided for CEO: none yet.

Routed, not done by this PH: security item LungNote 09d85a20 (fix proposal to CTO Main); ADR 0009
PH row in Agents-Rules (Mac-only, reminder only).
