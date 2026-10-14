# CooGate — STATUS (PH #adb2edb0, owner CTO Main #c34459eb, host contabo, budget $0)

Goal: SomPong (COO) creates and delegates its own researcher workers through org-coo-gate end to end on
Contabo, and the leaked org_coo credential is rotated with the units re-pointed to the landed Core.
Authority: CEO card Q-20261013-1948-4a33 (option 1); rulings Q-20261013-2010-091c, Q-20261013-2111-5ff5,
Q-20261013-2053-bf0f. Handoff: state/handoff/2026-10-14/cto-afe760fe.md.

Progress = milestones done / 5.

| # | Milestone | State | Evidence |
|---|---|---|---|
| M1 | org-coo-gate + org-coo-dispatch active, socket, `listening … for uids [0, 994]` | fix pushed, card to re-raise | RUN-20261014-0237-2c9e ran 09:47 TH → 226/NAMESPACE; fix 25a55d10 (PR #257); card bytes installing from Core sent to CTO Main |
| M2 | SomPong restarted on new code + `coo_mcp_server --cli ping` passes | waiting on card | fix 3f4faa2f (PR #254) landed via PR #255 = 3d9f9c61, live Core 475515d3; restart card RUN-20261014-0249-a97d (expires 10:49 TH) |
| M3 | live researcher task done + runner_fit row | not started | — |
| M4 | rotation + re-point to Core + remove coo-research-delegate worktree | waits CEO Infisical grant | — |
| M5 | close-out + Skill learning | not started | — |

## Blocker
- M1: PR #257 (25a55d10) must land in live Core, then CTO Main raises the gate card. Waiting on CTO Main since 09:56 TH.
- M4: Infisical Org-Coo Developer grant for `contabo` (CEO, Q-20261013-2053-bf0f). Waiting on the CEO since
  2026-10-13.

## Decided for CEO
- (none yet)

## Log
- 2026-10-14 09:35 TH: org-coo-gate failed, org-coo-dispatch active, SomPong tmux created 2026-10-08 (old code).
  The worktree is at 5e68f4b5 and clean, and the socket-dir fix is in Core.
- 2026-10-14 ~09:45 TH: on Core HEAD, test_spawn_coo dry-run is red: the coo allowed-tools list lacks
  ask_run/ask_run_wait/ask_ceo, because coo_mcp_server (2575f9b4) replaced the org server. Reported to CTO
  Main, who cancelled the restart card. Fix 3f4faa2f adds the three tools: they call tools/ask_run.py over
  HTTPS with SomPong's token and hold no hub credential.
- 2026-10-14 09:49 TH: PR #254 landed (batch PR #255 = 3d9f9c61), live Core 475515d3 serves 11 coo tools; CTO Main re-raised the restart card RUN-20261014-0249-a97d.
- 2026-10-14 09:47 TH: gate card ran; org-coo-gate hit its start limit with 226/NAMESPACE (ReadWritePaths on a missing /run dir kills the + pre-step's namespace). Probed and fixed with `ReadWritePaths=-…` + reset-failed in install.sh: 25a55d10, PR #257.
