# SafeRestart — STATUS
Progress: 6/10 · next: #451 lands → P3d post-fix sessions-only run, then P3e night reboot · waits on: CTO Main merge card for #451 · due: P3d Tue 27 Oct 23:00 TH, P3e Thu 29 Oct 07:00 TH

PH #47c4051c (CTO lane, Contabo; replaces #85f7b414, lost in the 19 Oct power-off, CEO Q-20261021-0312-9cba) · owner CTO Main #c34459eb · brief `state/ph-briefs/project_head-47c4051c.md`
Goal: a Restart card that saves every session, restarts the box and resumes the work at the lowest token cost.
Targets: P1+P2 by Sat 17 Oct 18:00 TH (met) · P3 was Sun 18 Oct (missed) → Fri 23 Oct 23:00 TH (missed: 23 Oct retest refused, see P3d) → **new targets (CTO Main 26 Oct): P3d by Tue 27 Oct 23:00 TH, P3e by Thu 29 Oct 07:00 TH** · P4, P5 after OrgMesh.

## Milestones (done ÷ total = %)
| # | Milestone | State | Evidence |
|---|---|---|---|
| P1 | `tools/restart_plan.py` read-only planner (§4 rules), writes `state/restart/<host>-<ts>.json` | done | merged ba8daad6 (card RUN-20261016-0214-ab11), PR #382 (task-2b10ed24, Codex; live dry run 8 sessions, C exact) |
| P2a | `--resume` in `spawn-ph.sh` / `tools/spawn_ph.py` | done | merged 2edc41c3, PR #383 (task-8b5013a8, Codex) |
| P2 | `tools/restart_run.py prep\|resume\|report` + idle-resume cost measured | done | merged 1b5a2349, PR #388 (task-8938b606, Codex 2 rounds + PH fixes; card RUN-20261016-0308-3507; live aa997ac4, 159 tests) |
| P3a | Clean + Restart cards, `org-resume.service` code | done | merged PR #395 @482b656c (task-63ea1c68, Codex + PH relay/park fixes; card RUN-20261016-0529-be14; live 4d5e04cf, 89 tests) |
| P3b | `org-resume.service` installed + enabled | done | card RUN-20261016-2344-881f (17 Oct 06:48 TH), `systemctl is-enabled` = enabled |
| P3c | Clean card, one real run | done | card RUN-20261017-0434-b373 done, exit 0 (closes done/saved PH sessions, restarts Browser Home Chrome) |
| P3d | Session restart test, no reboot (prep → resume → report) | passed 26 Oct; one post-fix run left | 22 Oct run (card RUN-20261021-0542-5442, unit org-sessrestart-20261022): try 1 held 01:10 TH (OrgMesh busy); try 2 at 01:27 saved 4, resumed **3/4** at 01:37: 3 PHs back, CTO Main not (`input never became empty`). Cause: old `org-cto-c34459eb.scope` still active, so the launcher's `systemd-run --scope --unit` was refused and the new pane died; CEO card RUN-20261022-0224-db91 relaunched it 09:25 TH (reported by COO). Fix: PR #423 @0d7e5edd (Codex task-c518aa4c, first pass; 109 tests; resume stops the leftover scope, a missing C-level gets a relaunch command card). Then retest. Fix merged #423 @04bb3072 (card RUN-20261022-0446-cd77). **23 Oct retest FAILED** (card RUN-20261022-0502-d3e5, unit org-sessrestart-20261023, 20:00 CEST 22 Oct, exit 1): prep refused, `pending resume manifest exists` (the 22 Oct run's manifest was never retired; PH knew and left it). The refused-prep fallback `resume` then replayed that old manifest and re-spawned the parked OrgMesh (7dcde548) + MyPasakonClip (e4149a4c) PHs. It also retired the manifest, so the state is clean now. Gate fix task-51c9f440 (retire a manifest >6 h old; fallback resume only for a marker this run wrote); spawn refused, disk 92%. Retest card RUN-20261024-1923-d11f, unit org-sessrestart-20261026, 25 Oct 18:00 UTC (01:00 TH 26 Oct), on-calendar in UTC because CEST→CET on 25 Oct. **26 Oct retest PASSED 4/4** (card RUN-20261024-1923-d11f, 01:04 TH): saved PH#47c, PH#b2f KhaoHomSurvival, CTO Main, CMO Main (COO service-managed, skipped); resume stopped the leftover `org-cto-c34459eb.scope` + `org-cmo-ef04792e.scope` (#423 working) and brought all 4 back; no parked PH spawned; `state/restart/contabo-resume.done-20261025T180446170714Z.json`, report card Q-20261025-1804-19bb. Gate fix = PR #451 (task-51c9f440 Codex + PH: marker bytes compared, so a stale marker prep replaced still gets the fallback resume; review task-0b13358b (Codex) found 2, both fixed: reboot-mode refused prep now rolls back too, naive/damaged marker timestamps age out by file time; 122 tests). After merge: one more sessions-only run |
| P3e | Real reboot test (night) | next (by Thu 29 Oct 07:00 TH) | timer `org-restart-20261018` stopped 17 Oct 17:12 CEST, never fired. Installed `/etc/systemd/system/org-resume.service` still lacks `Environment=HOME=/root` from #406 (`org-resume.sh` exports HOME itself, so it works; reinstall at P3e) |
| P4 | winbox card + logon Scheduled Task | follow-up | out of 17 Oct scope (CTO Main); waits on OrgMesh P3/P4 |
| P5 | Mac LaunchAgent (Mac CTO/PH builds) | follow-up | out of 17 Oct scope (CTO Main); waits on OrgMesh P3/P4 |

- **Shared files with PH#73c HostSpawn** (CTO Main 16 Oct): `tools/spawn_ph.py`, `scripts/spawn-ph.sh`. SendMessage HostSpawn before landing; the second PR rebases; CTO Main decides on disagreement. P4/P5 build on HostSpawn. HostSpawn PR #380 (spawn_ph.py only, merging 16 Oct): whichever lands second rebases.

- **Idle resume costs nothing until the first message** (16 Oct 02:37Z probe): `claude --resume <uuid> --fork-session` on a 67k transcript sat at an empty ❯ for 120 s; no jsonl created or touched → no API request. Option ⑤ holds.

- Docker: all 15 containers have restart policies (`always`/`unless-stopped`; org-postgres `unless-stopped`). pm2 has no startup unit, so `claudeflow-cron-scheduler` will not return after a reboot (already failing; CTO Main files it).

- **19 Oct 13:51 CEST power-off was unprepared**: logind "Power key pressed short" (panel/ACPI), no pending file, so org-resume skipped (`ConditionPathExists`) and every session was lost. The cards only cover a restart we start ourselves; an outside power-off needs a handoff written ahead (STATUS files did the job this time).

## Blockers
- (none)

## Decided for CEO
- LINE webhook redelivery is **off**; CEO accepts losing 1–3 min of LINE messages per reboot (Q-20261016-2344-a725). The OA-side handling (safe window, tell users to resend) belongs to LineAutomation: PASAKON/MoonieX-LineAutomation#4.
