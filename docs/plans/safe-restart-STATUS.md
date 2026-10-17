# SafeRestart — STATUS

PH #85f7b414 (CTO lane, Contabo) · owner CTO Main #c34459eb · brief `state/ph-briefs/project_head-85f7b414.md`
Goal: a Restart card that saves every session, restarts the box and resumes the work at the lowest token cost.
Targets: P1+P2 by Sat 17 Oct 18:00 TH · P3 Sun 18 Oct · P4, P5 after.

## Milestones (done ÷ total = %)
| # | Milestone | State | Evidence |
|---|---|---|---|
| P1 | `tools/restart_plan.py` read-only planner (§4 rules), writes `state/restart/<host>-<ts>.json` | done | merged ba8daad6 (card RUN-20261016-0214-ab11), PR #382 (task-2b10ed24, Codex; live dry run 8 sessions, C exact) |
| P2a | `--resume` in `spawn-ph.sh` / `tools/spawn_ph.py` | done | merged 2edc41c3, PR #383 (task-8b5013a8, Codex) |
| P2 | `tools/restart_run.py prep\|resume\|report` + idle-resume cost measured | done | merged 1b5a2349, PR #388 (task-8938b606, Codex 2 rounds + PH fixes; card RUN-20261016-0308-3507; live aa997ac4, 159 tests) |
| P3a | Clean + Restart cards, `org-resume.service` code | done | merged PR #395 @482b656c (task-63ea1c68, Codex + PH relay/park fixes; card RUN-20261016-0529-be14; live 4d5e04cf, 89 tests) |
| P3b | `org-resume.service` installed + enabled | done | card RUN-20261016-2344-881f (17 Oct 06:48 TH), `systemctl is-enabled` = enabled |
| P3c | Clean card, one real run | card up | RUN-20261017-0434-b373 (dry run: closes 0, restarts neko-pilot) |
| P3d | Session restart test, no reboot (prep → resume → report) | waiting CTO "go" | dry run 17 Oct: 8 sessions, 0 warnings, 0 workers, extra ≈1.09 M |
| P3e | Real reboot test 02:00 TH Sun 18 Oct | timer set | timer `org-restart-20261018` (card RUN-20261016-2344-2539) |
| P4 | winbox card + logon Scheduled Task | follow-up | out of 17 Oct scope (CTO Main); waits on OrgMesh P3/P4 |
| P5 | Mac LaunchAgent (Mac CTO/PH builds) | follow-up | out of 17 Oct scope (CTO Main); waits on OrgMesh P3/P4 |

- **Shared files with PH#73c HostSpawn** (CTO Main 16 Oct): `tools/spawn_ph.py`, `scripts/spawn-ph.sh`. SendMessage HostSpawn before landing; the second PR rebases; CTO Main decides on disagreement. P4/P5 build on HostSpawn. HostSpawn PR #380 (spawn_ph.py only, merging 16 Oct): whichever lands second rebases.

- **Idle resume costs nothing until the first message** (16 Oct 02:37Z probe): `claude --resume <uuid> --fork-session` on a 67k transcript sat at an empty ❯ for 120 s; no jsonl created or touched → no API request. Option ⑤ holds.

- Docker: all 15 containers have restart policies (`always`/`unless-stopped`; org-postgres `unless-stopped`). pm2 has no startup unit, so `claudeflow-cron-scheduler` will not return after a reboot (already failing; CTO Main files it).

## Blockers
- (none)

## Decided for CEO
- LINE webhook redelivery is **off**; CEO accepts losing 1–3 min of LINE messages per reboot (Q-20261016-2344-a725). The OA-side handling (safe window, tell users to resend) belongs to LineAutomation: PASAKON/MoonieX-LineAutomation#4.
