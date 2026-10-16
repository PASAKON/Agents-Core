# SafeRestart — STATUS

PH #85f7b414 (CTO lane, Contabo) · owner CTO Main #c34459eb · brief `state/ph-briefs/project_head-85f7b414.md`
Goal: a Restart card that saves every session, restarts the box and resumes the work at the lowest token cost.
Targets: P1+P2 by Sat 17 Oct 18:00 TH · P3 Sun 18 Oct · P4, P5 after.

## Milestones (done ÷ total = %)
| # | Milestone | State | Evidence |
|---|---|---|---|
| P1 | `tools/restart_plan.py` read-only planner (§4 rules), writes `state/restart/<host>-<ts>.json` | done | merged ba8daad6 (card RUN-20261016-0214-ab11), PR #382 (task-2b10ed24, Codex; live dry run 8 sessions, C exact) |
| P2a | `--resume` in `spawn-ph.sh` / `tools/spawn_ph.py` | done | merged 2edc41c3, PR #383 (task-8b5013a8, Codex) |
| P2 | `tools/restart_run.py prep\|resume\|report` + idle-resume cost measured | PR open | PR #388 @f0248528 (task-8938b606, Codex 2 rounds + PH worker-skip fix; 107 tests; live prep dry run OK) |
| P3 | Contabo Clean + Restart cards, `org-resume.service` | — | |
| P4 | winbox card + logon Scheduled Task | — | |
| P5 | Mac LaunchAgent (Mac CTO/PH builds) | — | |

- **Shared files with PH#73c HostSpawn** (CTO Main 16 Oct): `tools/spawn_ph.py`, `scripts/spawn-ph.sh`. SendMessage HostSpawn before landing; the second PR rebases; CTO Main decides on disagreement. P4/P5 build on HostSpawn. HostSpawn PR #380 (spawn_ph.py only, merging 16 Oct): whichever lands second rebases.

## Blockers
- (none)

## Decided for CEO
- (none)
