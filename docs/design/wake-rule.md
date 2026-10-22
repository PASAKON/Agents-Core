# Wake only on a real event — PROPOSAL

22 October 2026. PH proposal for CEO approval. No policy or live job changes.

Wake CXO and PH sessions only for a real event; keep worker supervision.
Run every check in a script with zero model turns; unchanged state stays silent.
Multiply clock-check intervals by 2 while any provider is over today's target, or 4 while AGY, ChatGPT and Claude all are.
Never stop those checks under budget pressure. A real event always wakes at once.
Record event IDs or state transitions so the same event does not wake twice.

## Events and existing producers

| Real event | Existing source |
|---|---|
| Run or question card answered | Run Inbox hub answer record and notification; `tools/ask_run.py` reads authoritative terminal records |
| Worker done, failed, or stuck | `tools/run_watch.py` Follower, `run_watch_driver.py`; `escalation_watch.py` detects stuck episodes |
| Deadline near | Deadline feed (`tools/email_ceo.py deadlines`) already produces CEO notices; route a deduplicated threshold event to the responsible PH/CXO in future |
| CEO letter | Mailbox delivery through `send_to_cxo` / transport; `mail_wake_sweep.py` catches deferred letters |

These producers are not all immediate PH/CXO routes today. Wire direct event delivery
separately from polling. Budget back-off must never delay an event already delivered.
For deadlines, arm a due-time event; do not let slower polling skip the threshold.

## Today's inventory and proposed changes

Read-only repository and installed-unit inspection. Systemd bus access was denied;
activation and full live coverage are **unverified**. Costs below are estimates per
session, for 24 hours, not measured billing. Script ticks are not model wakes.

| Source / check | Cadence; check needs model? | Wake trigger; rough wakes/day | Decision and change |
|---|---|---|---|
| Mail sweep / eligible unread letters | 60 s; zero-model | Event after debounce; 0 idle, traffic-dependent | Keep gate; back off polling; bypass debounce for real events |
| Run Watch driver / run transitions, lifecycle | 60 s; zero-model | Events plus start/restart; 0 idle, event-dependent | Keep gate; back off checks; review restart and batching paths |
| Escalation watch / stalls and held blockers | 5 min; zero-model | New episode plus one hourly reminder; up to 2/episode | Back off; replace unchanged reminder with a new deadline/stuck transition |
| Overnight self-wake skill / night plan | ~50 min plus 2 h backup; model | Clock; ~41/day | Change to event-driven script checks; back off checks, preserve both supervision layers |
| `/loop`, ScheduleWakeup, CronCreate in skills/roles | Session-specific; model when fired | Clock; 24–1,440/day at 60–1 min | Change to event-driven; inspect static candidates before approval |
| Monitor or background sleep loops / worker state | Commonly 60 s; script until output | Event if quiet; Monitor re-arm may cost 48/day | Keep silent event checks; back off polls; avoid model re-arm turns |
| Tool-value report / weekly metrics | Weekly; zero-model check | Clock report to COO; 1/week | Change to event-driven actionable finding; do not wake for unchanged metrics |
| Secretary waker / reply letters | 60 s; zero-model check | Pending mail; 0 idle | Keep; adjacent secretary scope, not a PH/CXO session |
| Idle-ping watcher / inactive iTerm pane | 60 s, ping after 5 min; zero-model | Idle clock; up to 288/day if repeatedly reset | Change to evidenced stuck event; Mac source, not verified on Contabo |

No hourly patrol waker was found in `tools/`, `scripts/`, or `lib/`; the sole
`patrol` match describes a visual effect. Other installed timers cover usage,
resource alerts, snapshots, certificates, CEO email/reminders, and metric collection.
They are not proven CXO/PH wakers. External scripts and persistent services need a
live follow-up. Pane-dialog watch creates a CEO question, not a direct model wake.

## Budget contract and audit limits

P1 supplies `tools/usage_budget.py` and `state/usage-budget/usage-budget.json`
(`{"ts", "day", "rows": {agy, chatgpt, claude, agy-claude}}`, each row with
`state: under | over | unknown`). `lib/wake_backoff.backoff_factor` reads it.
Missing data or data older than 30 minutes means factor 1 (fail open). Unknown is
not over. Any bar provider over means 2; all three (agy, chatgpt, claude) over means 4.
Invalid or future timestamps fail open.

`python tools/wake_audit.py [--json]` reads timers and service commands, plus skill
Markdown. It flags known direct clock wakers and scheduling primitive candidates.
Comments, examples, and prohibitions in skills can be false positives. Monitor and
sleep mentions require review, not an automatic violation. Known script gates are
a reviewed allowlist, not proof of all runtime paths. Unknown wrappers can escape
classification. Exit 1 means flags; exit 2 means incomplete discovery without flags.

## PROPOSAL — IRON-RULES and PH/CXO role text

**IRON-RULES:** Automatic CXO/PH wakes require a new answered card, worker
done/failed/stuck event, approaching deadline, or CEO letter. A zero-model script
checks first. An unchanged check must not spend a model turn. Retain supervision.
Slow clock checks by 2 when any provider is over target and by 4 when all three are over.
Never stop them. Events wake immediately. Missing/stale budget data means no slowdown.

**PH/CXO roles:** Use durable event producers and silent script checks to supervise
workers. Deduplicate events. Keep a backup check with the budget interval above.
Do not schedule a model heartbeat to discover that nothing changed. Propose policy
and routing changes to the CEO; this draft grants no permission to change them.
