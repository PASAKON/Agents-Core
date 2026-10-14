# CooGate — STATUS (PH #adb2edb0, owner CTO Main #c34459eb, host contabo, budget $0)

Goal: SomPong (COO) creates and delegates its own researcher workers through org-coo-gate end to end on
Contabo, and the leaked org_coo credential is rotated with the units re-pointed to the landed Core.
Authority: CEO card Q-20261013-1948-4a33 (option 1); rulings Q-20261013-2010-091c, Q-20261013-2111-5ff5,
Q-20261013-2053-bf0f. Handoff: state/handoff/2026-10-14/cto-afe760fe.md.

Progress = milestones done / 5.

| # | Milestone | State | Evidence |
|---|---|---|---|
| M1 | org-coo-gate + org-coo-dispatch active, socket, `listening … for uids [0, 994]` | **done** 10:04 TH | card RUN-20261014-0301-38b7 @ fix 25a55d10 (landed 2bd6e650, Core 4c6d62b7); socket srw-rw-rw- org-coo-gate; journal 05:04:00 CEST `listening … for uids [0, 994]`; both units' ExecStart under /opt/MoonieXHQ/Agents/Core (gate --path /) |
| M2 | SomPong restarted on new code + `coo_mcp_server --cli ping` passes | **done** 10:04 TH | card RUN-20261014-0249-a97d; tmux sompong created 10:04:11 TH; ping ok:true uid 994 roles [researcher, data_analyst, browser_operator] |
| M3 | live researcher task done + runner_fit row | **done** 10:27 TH | task-b7a6f0a3 (researcher, codex): created 03:26:05Z → coo_delegate_request (gate) → coo_dispatched → coo_runner_start → review 03:26:58Z → coo_close_request → done 03:27:05Z; runner_fit row by coo_dispatch: bucket codex, size S, 0.8 min, "Listed all 6 files in deploy/coo-gate with one line each; matches ls; nothing changed" |
| M4 | rotation + re-point to Core + remove coo-research-delegate worktree | waits CEO Infisical grant | re-point to Core done at M1; write probe `infisical_setup.py mkdir` 08d38e9b (branch ph-adb2edb0/infisical-mkdir) |
| M5 | close-out + Skill learning | not started | — |

## Blocker
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
- 2026-10-14 10:04 TH: M1 + M2 done (gate on Core, SomPong restarted, ping ok). Units re-pointed to Core already (M4 half); secret path still / until rotation.
- 2026-10-14 10:19 TH: M3 try 1 failed at step 1: SomPong's org MCP CONNECTION_CLOSED (Claude Code 2.1.296 ignores the MCP entry's cwd → ModuleNotFoundError 'runners'). CTO Main fixed it with PYTHONPATH on the org entries (4b50e9e3, PR #261, Core 340ba2cb); restart card RUN-20261014-0319-56d7. Disk was 91%: removed my two merged worktrees → 88%.
- 2026-10-14 10:27 TH: M3 done, task-b7a6f0a3 + runner_fit (SomPong PASS, relayed by CTO Main). Found M4 hazard: rotation changes the PG password before `put`; added `mkdir` write probe (08d38e9b) to chain in front.
