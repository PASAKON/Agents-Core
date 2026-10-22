# REPORT task-653c3900

Implemented the draft policy, read-only audit, and pure back-off helper. No timers,
services, skills, role documents, or IRON files were changed. No enforcement or
back-off wiring was added.

## Files changed

- `docs/design/wake-rule.md`: short proposal, event mapping, inventory and role text.
- `tools/wake_audit.py`: systemd discovery with explicit incomplete fallback;
  known command classifier and static skill scan; human and JSON output.
- `lib/wake_backoff.py`: fail-open factor 1/2/4 with timestamp validation.
- `tests/test_wake_backoff.py`, `tests/test_wake_audit.py`: isolated policy and unit-text tests.
- This report.

## Validation

`python3 -m unittest tests.test_wake_backoff tests.test_wake_audit`

**11 tests passed.** Only the new tests were run. `git diff --check` passed.
The runner has `python3`, not `python`; the equivalent audit command was
`python3 tools/wake_audit.py`. It returned 1. Exact output:

```text
INCOMPLETE: systemd unavailable; installed unit-file fallback, activation unknown
FLAG escalation-watch.timer: stuck event gate plus timed unchanged-episode reminder
EVENT run-watch-driver.timer: Follower events and active-run lifecycle; review restarts
FLAG tool-value-report.timer: no reviewed event gate for command
FLAG ALL_Protocol_RunInbox/SKILL.md: CronCreate
REVIEW CMO_Knowledge_Flow_Omni1.1/SKILL.md: Monitor
REVIEW CMO_Knowledge_Seedance2.5_Higgsfield/SKILL.md: sleep
REVIEW CMO_Procedure_BlackLiquidity_Cut/SKILL.md: Monitor
FLAG CMO_Workflow_MimiPage_Weekly/SKILL.md: CronCreate
REVIEW CTO_Gate_MergeChecklist/SKILL.md: sleep
REVIEW CTO_Procedure_Bedrock_SkyScene/SKILL.md: Monitor, sleep
REVIEW CXO_Protocol_DevSpawn/SKILL.md: Monitor, sleep
FLAG CXO_Protocol_OvernightSelfWake/SKILL.md: /loop, CronCreate, Monitor, ScheduleWakeup, sleep
REVIEW de-ai-ify/SKILL.md: Monitor
13 sources; 5 flagged; 1 inventory errors
```

## Inventory

Installed files and repository evidence only; not a complete live Contabo audit.
Wakes/day estimates are per session and do not count zero-model script polls.

| Source | Check | Frequency | Model for check? | Trigger; wakes/day | Proposal |
|---|---|---|---|---|---|
| Mail wake sweep | Eligible pending mail | 60 s | No | Mail after debounce; 0 idle | Keep gate, immediate real events, back off checks |
| Run Watch driver | Run transitions and lifecycle | 60 s | No | Event/start/restart; variable, 0 idle | Keep; back off checks; review lifecycle |
| Escalation watch | Stalled/held episodes | 5 min | No | Event + hourly reminder; ≤2/episode | Back off; remove unchanged reminder wakes |
| Overnight self-wake | Night plan status | 50 min + 2 h backup | Yes | Clock; ~41 | Replace model heartbeat with script |
| Other scheduling primitives in skills/roles | Session work | Variable | Yes on wake | Clock; 24–1,440 at hourly–minutely | Review and convert to events |
| Monitor/background sleep | Worker changes | Often 60 s | No until output/re-arm | Event; re-arm can cost 48 | Keep silent checks, back off |
| Tool-value report | Weekly metrics | Weekly | No | Clock to COO; 1/week | Wake only on actionable change |
| Secretary waker (adjacent scope) | Reply mailbox | 60 s | No until mail | Event; 0 idle | Keep |
| Idle-ping watcher (Mac) | Inactive pane | 60 s; 5 min threshold | No | Idle clock; ≤288 if repeatedly reset | Use real stuck transition |
| Pane-dialog watcher | Unanswered permission dialog | 60 s installer | No | CEO question, not direct CXO turn | Retain event check |

No hourly patrol waker found in the three requested code directories. Role docs
were searched for the requested primitives; no matches were returned. Skill
matches are reported above, including historical/prose false positives.

Other installed timer names inspected: agy-usage-feed, ceo-deadline-feed,
ceo-digest, claude-usage-monitor, codex-usage-feed, contabo-invoice-reminder,
disk-push, household-reminders, mooniex-console-cert-renew, org-snapshot,
quota-snapshot, ram-push, run-mail-sender, spend-guard, tool-value-collect,
zai-usage-monitor. None is established here as a direct PH/CXO waker;
external programs require follow-up. Deadline/Run mail services target CEO
notifications and are potential event producers, not proof of immediate PH delivery.

## Branch and delivery

Current branch: `agent/codex-task-653c3900`.
Base HEAD: `890b021d8fb867d278da97137c90755c9a59f15a`.
Changes remain uncommitted for the launcher, as the worker contract requires.
No PR created and nothing merged.

## Blockers

- `git fetch origin` failed because linked-worktree Git metadata is read-only.
  The requested `ph/usagebudget-p3` branch from freshly fetched `origin/main`
  could not be created. Launcher/PH must transplant these files onto that base,
  commit and push, then open a PR against `main` titled
  **UsageBudget P3: wake rule draft + wake_audit**. Do not merge.
- `systemctl list-timers --all` failed: `Failed to connect to bus: Operation not permitted`.
  Full effective-unit inspection and active-timer inventory remain for PH on Contabo.
  Installed `/etc/systemd/system` unit files were read without modification.
- P1 is absent in this checkout. Confirm the proposed `updated_at`/`providers`
  JSON interface before integrating the helper. No live budget state was changed.
- Static classification is intentionally bounded: unknown wrappers, other unit
  directories, dynamically generated jobs and live in-session schedules are not
  fully discoverable. Primitive mentions are candidates, not proof of active jobs.

## Skill learning

- (none)
