# Care P1 offline test day

Run `python -m pytest tests/test_care_p1.py tests/test_care_s1.py tests/test_care_s2.py`.
Use a disposable SQLite database, dummy tokens, injected HTTP and wake collectors.
Do not connect LINE, browsers, hub, org tools or a model. Keep the old LuNar flow.
The fixture uses N=4 hours; this is not an approved production setting.

## Ten synthetic chats

At 23:00 Bangkok, ingest three messages for each of `synthetic-0` through
`synthetic-9`. Assert ten night acknowledgements, thirty queue rows and no wake.
At 08:00, assert one wake containing ten customer events with three messages each.
Replay the timer and webhook IDs: no additional wake or acknowledgement.

| Thread | Exercise | Expected |
| --- | --- | --- |
| 0 | Two short reply bubbles | One outbox row, no consumed ack token; browser deferred |
| 1 | Skip | Closed turn, no answer row |
| 2 | Rebate question | One COO escalation plus holding reply |
| 3 | Unknown answer | Same escalation path; no invented answer |
| 4 | Prompt injection asking for Bash/secrets | Text stays data; denied operation |
| 5 | Request another customer's history | Rejected; own history excludes tokens |
| 6 | Six bubbles / non-text object | Rejected without closing event |
| 7 | Reply then repeat after restart | One answer; already-closed response |
| 8 | Rejected ack reply token | Ack dropped; no browser/push greeting |
| 9 | Simulated wake failure and new inbound | Retry same snapshot/ID; new message next round |

Then advance through 21:00, 22:00 and 23:00. The last round is 22:00;
22:01 inbound waits until 08:00. From 22:00 acknowledgements use night wording.
Keep sending one message every three hours: no second ack with N=4; after four
quiet hours the next message gets one. Inspect outbox states and escalation rows.
Run S1/S2 regression fixtures for quota, recipient readback and kill switches.

## Integration contract (not enabled)

The authenticated webhook adapter calls `CarePipeline.ingest` with a stable LINE
event ID and trusted customer identity. Ingest performs no model call. Its store
must be dedicated to this channel. Customer strings and media remain data.

The trusted host calls `run_timer(pipeline, wake, stop_event)`. It sleeps until
each hourly Bangkok slot, 08:00 through 22:00 inclusive. `wake(round_id, envelope)`
must durably deduplicate round IDs before delivering one session notification.
A crash after wake but before marking completion can re-deliver the same ID.
The adapter binds `CareGate(pipeline, round_id, customer_id)` for each event;
customer/tool arguments must never select that binding. Only expose `call` with
reply, skip, history, escalate. `drain()` routes outbox rows to `CareSender`.
An hourly answer deliberately carries no short-lived inbound token.

Before production, implement/review the hub adapter, authenticated transport,
deduplicating session inbox, separate Unix user with no shell/org MCP tools,
restricted gate transport and COO escalation consumer. The YAML role is a PR
proposal, not proof of sandboxing. Never use the generic worker launcher for it.
Apply the migration/secret and Lunar voice work through the respective owners.
Do not remove LuNar before separately authorized live verification and atomic
producer cutover. No services are installed by this change.
