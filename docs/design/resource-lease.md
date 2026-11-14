# Hub resource leases — Phase B specification

Order O-20261114-1701-56fb. Proposed contract, not deployed behavior. This phase
adds only this design, a deterministic reference harness and reports. The registry,
schema, Python library, CLI and HTTP routes below are Phase C deliverables.

## Evidence and scope

Read-only inputs (absolute roots retained so citations are reproducible):

- A1 = `/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-52f759e8/docs/reports/org-queue-audit/A1-resources.md:7`.
- A2 = `/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-e1f4e689/docs/reports/org-queue-audit/A2-correctness.md:6`;
  proofs = `/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-e1f4e689/tests/test_queue_audit_a2.py:34`.
- A3 = `/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-b485f75f/docs/reports/org-queue-audit/A3-incidents.md:169`.

The present hub helper reads then replaces (`lib/db.py:1360`); its PG translator
does unconditional conflict update (`lib/db_pg.py:378`). Console's immediate 409
is not a queue (`tools/home_lock.py:92`). A2 is authoritative for its audited
revision: do not infer exact current implementation semantics from A3's historical
incident descriptions. In particular, path prefix behavior differed across revisions.

## One primitive and one authority

A named resource has one hub row and three possible admission policies:

| Kind | Admission | Release/expiry |
| --- | --- | --- |
| mutex | At most one current holder | Returns the slot |
| pool | At most capacity current holders (one unit per request initially) | Returns one slot |
| rate | At most N grants in rolling interval `(now() - window_s, now()]`, and `now() >= cooling_until` | Ends holder authority; never refunds a grant |

All use the same waiter, owner, fencing, heartbeat, event and wake machinery.
Rate windows measure grants, not completions. A provider exit such as ChatGPT exit
5 sets `cooling_until` through an authenticated far-side report; extend by MAX,
never shorten from an ordinary client. Unknown reset time means administratively
paused until a verified reset, not guessed entitlement. A reset event may explicitly
start a new quota epoch and clear cooling; duplicate provider event IDs are ignored.
Paid balances with no reset are conservative grant budgets with manual verified
replenishment; variable-cost reservations need units/cost accounting in a later
extension, not an invented provider capacity. A1 distinguishes these shapes.

Hub time alone sets creation, expiry, max-hold deadlines, cooling and windows.
Default heartbeat 5 s, renewable TTL 10 s, hard max_hold 30 s in tests; production
values are registry policy. `expires_at = min(now()+2*heartbeat_s, started_at+
max_hold_s)`. Renew never resets started_at. At the hard limit revoke, send owner
a letter and schedule the next eligible waiter even when the owner remains alive.
Long jobs checkpoint and requeue; they cannot monopolize by renewing forever.

Liveness uses stable owner/session ID plus host boot ID, PID start identity and
tmux/session observations. Reuse injected probes from `lib/run_liveness.py:216`,
`lib/run_liveness.py:220` and classification vocabulary at `lib/run_liveness.py:251`.
Do not blindly reuse its run-status filtering or spawn/report grace as lease TTL:
quiet is alive; confirmed all-process/session death revokes within one heartbeat
pass; unreachable/unknown is not confirmed dead and waits for TTL. A compacted
session keeps its identity and heartbeat supervisor, even when its child PID changes.
The tests' fake observation represents an already-confirmed verdict.

Each new grant returns a monotonically increasing token from a non-resetting PG
sequence. Every renew, release and guarded write binds resource, owner, grant ID
and token; no owner-label-only authorization. Server auth supplies the identity.
The resource actuator rejects revoked/expired tokens as well as older tokens.
Token comparison alone is insufficient before the next holder writes. A gateway
must validate current authority at action time and serialize validation with the
effect where possible. Direct CDP/file side effects cannot be made fenced by a
number alone: require the owning browser/host agent to enforce it, stop an old
operation and acknowledge quiescence before allowing a conflicting new effect.
Logical override is immediate; physical stop latency remains an integration risk.

## Registry proposal: config/resources.yaml

No config file is created in Phase B. This is the exact proposed format. Resolve
exact names before patterns; reject ambiguous patterns, unknown names, invalid
capacity, max_hold less than two heartbeats, or a paid fail-open policy. Materialize
resolved policy/version into `leases` so all hosts use the same policy snapshot.
No caller chooses its own priority or approval status. Lower priority number wins.

```yaml
version: 1
defaults:
  heartbeat_s: 5
  max_hold_s: 300
  priority_classes: {ceo: 0, urgent: 5, normal: 10, background: 20}
  queue_cap: 1000
  on_hub_down: fail_closed
  needs_ceo_card: false
  paid: false
  wake: {waiter: owner_session, fallback: owner_cto}
resources:
  - {pattern: 'chatgpt:<host>:<port>', alias: 'chrome:<host>:<port>'}
  - {pattern: 'chrome:<host>:<port>', kind: mutex, capacity: 1, max_hold_s: 1800}
  - {pattern: 'host:<host>:workers', kind: pool, capacity_from: 'hosts.<host>.max_workers', max_hold_s: 3600}
  - {pattern: 'host:<host>:disk', kind: pool, capacity: 1, admission: fresh_disk_band, max_hold_s: 3600}
  - {name: 'host:contabo:cpu-exception', kind: mutex, capacity: 1, max_hold_s: 3600}
  - {pattern: 'proj:<project>:path:<path>', kind: mutex, capacity: 1, max_hold_s: 3600}
  - {pattern: 'quota:<bucket>', kind: rate, rate_from: 'verified_quotas.<bucket>', paid: true, max_hold_s: 3600}
  - {pattern: 'browser_operator:<host>', kind: pool, capacity_from: 'hosts.<host>.max_browser_operators', max_hold_s: 1800}
  - {pattern: 'render:<host>', kind: mutex, capacity: 1, admission: fresh_ram_cpu, max_hold_s: 3600}
  - {pattern: 'ph:<owner>:workers', kind: pool, capacity: 2, max_hold_s: 3600}
```

`capacity_from` / `rate_from` are registry-loader references to reviewed values,
not permissive runtime defaults: missing values disable admission. `rate_from`
resolves `{grants, window_s}`. Pattern rows are not a live inventory. A browser
home is resolved via its host/profile/account mapping before alias expansion;
two website names in one profile must resolve to the same chrome key. Account
quota keys remain separate from browser locks. Seedance through fal consumes
the fal account bucket, not a second balance (A1 inventory).

Disk and RAM gates consume fresh host-agent telemetry with an expiry; stale
telemetry closes admission. Capacity reservations do not create free RAM or disk.
Disk cleanup/worker completion publishes a readiness event which schedules waiting
requests immediately. Orange and red both enqueue. Dynamic capacity reduction
blocks new grants without silently evicting holders. All money-spending resources
fail closed during hub loss; free resources may explicitly choose `uncoordinated`
only for advisory, nonexclusive work. That result has no fencing token and is never
reported as a lease. Browser, screen and path resources remain fail closed.

## API: three surfaces, one state machine

Python `lib/lease.py` exports `lease(name, purpose, wait_s=0)` and
`lease_many(names, purpose, wait_s=0)`. Identity comes from an authenticated
launcher session, not purpose text. Enter queues once with an idempotency key,
waits up to wait_s using notifications, then returns a handle with request_id,
token, expires_at and `assert_valid()`. Timeout cancels that synchronous waiter;
durable asynchronous admission is an explicit `acquire` operation. Context entry
starts a supervisor heartbeat thread; exit stops/joins it and releases in finally,
including exceptions. A renewal failure marks the handle lost and cancels guarded
work; it must not silently continue. Server expiry is the fallback if exit cannot
reach the hub. CLI/HTTP callers run their own launcher heartbeat.

`tools/lease.py acquire|renew|release|status|wait` uses the identical library.
Acquire returns JSON state (`granted`, `waiting`, `awaiting_approval`, `refused`),
request ID, optional token, reason, position and deadlines. Wait attaches to an
existing durable request; retrying acquire with its idempotency key never duplicates
it. Renew/release require request and token. Status is read-only. Cancellation,
provider cooling, approval and override are authenticated administrative operations,
not a freely supplied CLI role flag.

Console exposes thin `/api/leases/acquire`, `/renew`, `/release`, `/status`, `/wait`
and event subscription routes with scoped host/session authentication, resource
allowlists and idempotency keys. Only Console holds DB credentials for those hosts.
Replace the home_lock route with a compatibility adapter to this service; never
maintain relay-locks.json as a second authority. DB/read/parse errors refuse admission
and leave the recorded holder intact. Purpose and logs must contain no credentials.

## Scheduling, claims and wake delivery

Queue order is `(priority_class, enqueued_at, enqueue_seq)` with FIFO within a
class. CEO priority jumps waiting ordinary work but never preempts a holder.
Requests awaiting a card are ineligible until approved; eligibility time becomes
their queue time. Queue caps refuse explicitly with `queue_full:<cap>` and do not
discard older entries. A dead waiter is skipped only after authoritative liveness
or explicit task cancellation, not because a queued task has no PID yet.

Acquire every requested name in canonical sorted order, in one transaction. A
request owns all names or none, including on exceptions. No hold-and-wait. A
blocked head reserves ordering on its intersecting resources; independent resources
may proceed. Rate credits are consumed only when the entire group commits.
Disallow nested acquisition outside a declared group. Path normalization rejects
string `touches`, traversal and ambiguous wildcards; expands task report templates
before admission. Project is a separate equality field, never SQL LIKE. Initially
use a conservative project-wide path mutex for directory/glob overlaps and require
all path users in that project to use the same mode. Exact-file mode can be enabled
only after directory users are migrated; mixing ancestor and child keys is unsafe.

States: awaiting_approval → waiting → claimed → acknowledged → terminal. A grant
reserves capacity and marks its waiter claimed in the same commit; it never pops
the row. Lookup/delegate failure preserves claim payload and retry reason. Dispatch
uses request ID as spawn idempotency key. On crash/expired unacknowledged claim,
reconcile whether spawn succeeded, then requeue with original ordering if it did
not. Never charge a second rate grant for retry of the same provider submission:
retain submission ID/consumption receipt; ambiguous outcomes require reconciliation.
Acknowledged dispatch hands heartbeat ownership to the running session.

Release/reap/reset schedules eligible heads and inserts wake outbox events in its
transaction. After commit the dispatcher immediately writes a mailbox letter and
calls the existing wake path (`tools/send_to_cto.py:166`, `tools/mail_wake.py:157`).
Use an actionable urgent lease-ready letter, not `report`/`fyi`, which may not wake
(`tools/send_to_cto.py:139`). One successful handoff requires one wake, not another
watchdog interval. Pool release wakes as many as available slots. Durable outbox
retry is at-least-once; receiver deduplicates by event/request ID. A failed wake
does not free a claimed slot early or erase its waiter. Crash after commit before
delivery is recovered by the outbox worker. Notify is a hint, not the durable log.

`gc_stale_tasks` excludes every nonterminal waiter/claim across hosts; explicit
cancel atomically removes its waiter, revokes grants and records cancellation.
Restart sweeps expiries without deleting queue rows. Confirmed death is processed
on each heartbeat tick; timer scheduling also targets cooling/window expiry.
Terminal task state changes release grants and invoke the same scheduler.

CEO emergency override revokes the chosen holder, increments fencing, writes its
stop letter and grants CEO in one transaction before ordinary queue scheduling.
CTO/CEO forced release requires authenticated authority plus reason and audit event.
Approval-required resources still require a verified card bound to resource,
request, purpose, actor and validity interval; approval is not a reusable boolean.
The reference model treats its injected role/card as already verified credentials.

## PostgreSQL schema and atomic grant

Proposed DDL; not executed here. One resource row serializes capacity decisions.
Holder JSON is bounded by configured capacity for mutex/pool; rate holders expire
independently of the durable grant ledger. `lease_events` is both audit and outbox.

```sql
CREATE SEQUENCE lease_fence_seq AS bigint;
CREATE TABLE leases (
  name text PRIMARY KEY,
  kind text NOT NULL CHECK (kind IN ('mutex','pool','rate')),
  project text,
  capacity integer NOT NULL CHECK (capacity > 0),
  window_s integer CHECK (window_s > 0),
  heartbeat_s integer NOT NULL CHECK (heartbeat_s > 0),
  max_hold_s integer NOT NULL,
  policy_version bigint NOT NULL,
  policy jsonb NOT NULL,
  holders jsonb NOT NULL DEFAULT '{}',
  cooling_until timestamptz NOT NULL DEFAULT '-infinity',
  quota_epoch bigint NOT NULL DEFAULT 0,
  next_check_at timestamptz,
  CHECK (max_hold_s >= 2 * heartbeat_s),
  CHECK (kind <> 'mutex' OR capacity = 1),
  CHECK (kind <> 'rate' OR window_s IS NOT NULL)
);
CREATE TABLE lease_waiters (
  request_id uuid PRIMARY KEY,
  resource text NOT NULL REFERENCES leases(name),
  group_id uuid NOT NULL,
  owner_session text NOT NULL,
  task_id text,
  priority integer NOT NULL,
  enqueue_seq bigint GENERATED ALWAYS AS IDENTITY,
  enqueued_at timestamptz NOT NULL DEFAULT now(),
  state text NOT NULL CHECK (state IN
    ('awaiting_approval','waiting','claimed','acknowledged','cancelled','done')),
  idempotency_key text NOT NULL,
  purpose text NOT NULL,
  payload jsonb NOT NULL,
  approval jsonb,
  fence bigint,
  claim_until timestamptz,
  UNIQUE(resource, owner_session, idempotency_key)
);
CREATE TABLE lease_events (
  event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  resource text NOT NULL REFERENCES leases(name),
  request_id uuid,
  event_key text NOT NULL UNIQUE,
  kind text NOT NULL,
  at timestamptz NOT NULL DEFAULT now(),
  fence bigint,
  quota_epoch bigint,
  actor text NOT NULL,
  payload jsonb NOT NULL,
  deliver_after timestamptz,
  delivered_at timestamptz,
  attempts integer NOT NULL DEFAULT 0
);
CREATE INDEX lease_due ON leases(next_check_at);
CREATE INDEX lease_project ON leases(project);
CREATE INDEX waiter_head ON lease_waiters(resource, priority, enqueued_at, enqueue_seq)
  WHERE state = 'waiting';
CREATE INDEX waiter_task ON lease_waiters(task_id, state);
CREATE INDEX waiter_claim ON lease_waiters(claim_until) WHERE state = 'claimed';
CREATE INDEX waiter_group ON lease_waiters(group_id);
CREATE INDEX event_rate ON lease_events(resource, quota_epoch, at) WHERE kind = 'grant';
CREATE INDEX event_outbox ON lease_events(deliver_after, event_id)
  WHERE delivered_at IS NULL AND deliver_after IS NOT NULL;
```

All mutation transactions use SERIALIZABLE, bounded retry on serialization failure
or deadlock with the same idempotency key. Lock resource rows in sorted name order
for groups; lock acquisition is not a separate SELECT decision about availability.
Enqueue, cancellation, cooling and grant also touch the resource row, preventing
phantom priority admissions. Expiry cleanup is a transaction transition before
admission, using SQL now(); stale entries may delay but never enable overgranting.

The following single-resource mutex/pool grant is the concrete one-statement
pattern. Parameters are authenticated/validated before execution. No SELECT-then-
INSERT and no INSERT OR REPLACE. The head selection is inside the SQL statement;
the conditional UPDATE is the grant linearization point. PG rechecks the updated
row or raises serialization failure on a competing resource write.

```sql
WITH head AS MATERIALIZED (
  SELECT * FROM lease_waiters WHERE resource = :name AND state = 'waiting'
  ORDER BY priority, enqueued_at, enqueue_seq LIMIT 1
), granted AS (
  UPDATE leases l SET holders = l.holders || jsonb_build_object(
    h.request_id::text, jsonb_build_object(
      'owner', h.owner_session, 'token', nextval('lease_fence_seq'),
      'started_at', now(), 'expires_at',
      now() + make_interval(secs => LEAST(2*l.heartbeat_s,l.max_hold_s))))
  FROM head h
  WHERE l.name = :name AND h.request_id = :request_id
    AND l.kind IN ('mutex','pool')
    AND (SELECT count(*) FROM jsonb_object_keys(l.holders)) < l.capacity
  RETURNING l.name, l.holders -> :request_id::text AS holder
), claimed AS (
  UPDATE lease_waiters w SET state = 'claimed',
    fence = (g.holder->>'token')::bigint,
    claim_until = (g.holder->>'expires_at')::timestamptz
  FROM granted g WHERE w.request_id = :request_id RETURNING w.*
)
INSERT INTO lease_events(resource, request_id, event_key, kind, fence, actor,
                         payload, deliver_after)
SELECT resource, request_id, 'grant:' || fence, 'grant', fence, owner_session,
       jsonb_build_object('wake',true), now() FROM claimed
RETURNING request_id, fence;
```

This SQL is a reviewable proposal, not an executed migration. For rate use the
same UPDATE pipeline, replace its
capacity predicate with `l.cooling_until <= now()` and a count of `grant` events
in the current quota_epoch with `at > now()-make_interval(secs=>l.window_s)` less
than capacity; insert quota_epoch in the returned grant event. SERIALIZABLE and
the common resource-row write prevent concurrent snapshot counts from overgranting.
Never prune rate events still inside the window. Renew/release predicates require
matching JSON owner/token and unexpired SQL timestamps. Group grants run this
statement for each sorted name in one transaction and roll back all if any fails;
group-aware head selection applies the ordering rule above, never partial commits.

`lib/db.py` owns schema migration and repository operations; `lib/db_pg.py` must
pass native PG constructs and translate bound `?` placeholders through its existing
translation path (`lib/db_pg.py:416`), not route lease writes through the old
replacement rewrite (`lib/db_pg.py:378`). Named placeholders in this document are
explanatory; production uses the repository's bound parameter API. PG schema types,
JSON operators, RETURNING, interval math, serialization retries and outbox commits
need scratch PostgreSQL integration tests in C. The Python model proves none of
those engine properties.

## Add a new queued system

Add one row under `resources`, inheriting the defaults above. The two integration
lines assume `lease` is imported and the named operation is available. Numbers
below are explicit example local policy, not claims about provider entitlement;
enable only after its owner confirms them. Resource actions must enforce `l.token`.

YouTube upload rate (one grant per hour for this example channel):

```yaml
- {name: 'quota:youtube:example-channel:uploads', kind: rate, rate: {grants: 1, window_s: 3600}, max_hold_s: 1800, paid: false, on_hub_down: fail_closed, needs_ceo_card: true}
```
```python
with lease('quota:youtube:example-channel:uploads', purpose='publish approved video', wait_s=3600) as l:
    upload_video(fencing_token=l.token)
```

Colab pool (one enabled slot in this example; reserve its separate account budget
and browser lease in a group when the execution path also needs them):

```yaml
- {name: 'colab:example-account:slots', kind: pool, capacity: 1, max_hold_s: 3600, paid: true, on_hub_down: fail_closed, needs_ceo_card: true}
```
```python
with lease('colab:example-account:slots', purpose='approved render', wait_s=3600) as l:
    render_on_colab(fencing_token=l.token)
```

Winbox physical screen (all desktop input users share this one name):

```yaml
- {name: 'screen:winbox', kind: mutex, capacity: 1, max_hold_s: 600, paid: false, on_hub_down: fail_closed, needs_ceo_card: true}
```
```python
with lease('screen:winbox', purpose='approved desktop operation', wait_s=600) as l:
    operate_desktop(fencing_token=l.token)
```

No new bespoke queue or polling loop. The two lines assume supporting gateway
enforcement already exists; they are not enough to retrofit an unfenced provider.

## Migration and rollback

Roll out in A3 order: paths; host capacity/disk; runner quotas; Chrome/ChatGPT;
renders/PH pools. For every wave first shadow-read and compare decisions, then
freeze old admissions/drains, snapshot with checksum and manifest, reconcile live
holders, import, compare counts and payload hashes, and switch a versioned routing
flag for all writers. Never run two authorities or destructive dual drains.

| Source | Cutover | Rollback |
| --- | --- | --- |
| host_queue.jsonl on each host | Freeze enqueue/drain; snapshot host+file+digest; map to host worker groups; preserve constraints and payload | Freeze new admissions; reconcile claimed spawns; export still-waiting rows in FIFO order to old format under old writer lock; atomic replace then switch all hosts |
| disk_queue.jsonl on each host | Same import; map red and previously unqueued orange to disk admission; use transactional inserts instead of file rewrites | Same export, enable serialized old writer adapter before old admission; never restore a stale snapshot over newly accepted work |
| budget_queue.jsonl on each host | Preserve original bucket/reset/model intent; map rate epoch; re-evaluate runner+model together at dispatch | Export nonterminal waits with verified reset times; drain active claims first; retain quota consumption receipts so rollback cannot refund spend |
| Console relay-locks.json / home_lock | Freeze HTTP grants and direct callers; import live owner+remaining TTL; map home aliases; switch route to hub | Fence/drain hub holders, restore reconciled nonexpired records, switch all clients; no simultaneous JSON and hub grants |
| pc_lease / exclusive.lock | Freeze borrowers; reconcile physical owner and CEO hold; require local actuator fencing; explicit CEO hold stays blocked until approval to transfer | Stop new hub input, quiesce borrowers, export current owner/hold to old protocol before switching desktop gate |
| Path locks / hub locks | Freeze task dispatch; validate touches; import only confirmed active ownership; queue pending/conflict rows; start conservative project mode | Stop new grants; drain/fence active tasks; export active owner/expiry only; restore old adapter with atomic grant guard, not known broken overwrite |

Every rollback can safely stop admissions if the legacy format cannot represent
current claims, approvals or fencing. Do not promise an online rollback to unsafe
legacy behavior. Snapshot originals remain immutable for audit. Import identity
is `(source host, frozen file digest, line ordinal)`; identical retries do nothing,
changed source under the same identity aborts. Store every raw row including
duplicate lines and malformed rows in import audit events; malformed entries block
cutover for review. Map duplicate logical task waits to one dispatch request but
retain every provenance entry. Cross-host order uses verified timestamps then
host/source/ordinal as deterministic tie-break; unknown timestamp order is recorded.
Import and counts commit together; partial import cannot delete old rows. The
reference test uses parsed frozen JSONL rows with source+ordinal keys; it does not
exercise a real filesystem parser, manifest or cross-host freeze.

Console relay_queue.db was not verified by A1/A2. Discover its schema in C before
designing an import adapter; no destructive migration is authorized by this doc.

## Audit-to-design acceptance map

These fixes are design obligations. Original A2 proofs import legacy production
modules and remain expected to fail in B; C must route those callers to the new
primitive and make all twelve proofs pass, not merely repoint them at this model.

| A2 bug | Required correction | Scenario coverage / C gap |
| --- | --- | --- |
| A2-001 | One conditional grant statement, SERIALIZABLE retry, fencing | 05, 09; real concurrent SQL in C |
| A2-002 | Separate project equality, no LIKE | 18 |
| A2-003 | Sorted all-or-none group transaction, exception rollback | 14; SQL abort injection in C |
| A2-004 | Durable row enqueue, no stale file snapshot writes | 05/16/21; concurrent enqueue persistence in C |
| A2-005 | Transactional import/enqueue, immutable source snapshot | 21; storage crash durability in C |
| A2-006 | Lookup errors keep claim/payload | 08 |
| A2-007 | Crash before dispatch ack retains reclaimable request | 08; real spawn idempotency in C |
| A2-008 | Global waiter/claim GC exemption | 17 |
| A2-009 | Reset invokes common scheduler and outbox immediately | 12 |
| A2-010 | SQL now() for every admission/deadline | 15 |
| A2-011 | Delegate failure retains claim until acknowledged | 08 |
| A2-012 | Hub/Console errors fail closed, no empty-state fallback | 07; HTTP failure injection in C |

| A3 priority (source section line) | Design element |
| --- | --- |
| 1 paths (A3:173) | Granted ownership only, normalized exact names/project fallback, atomic groups, GC protection, release wake |
| 2 host+disk (A3:180) | Worker pool and disk gate, CPU-exception mutex, fresh telemetry, orange/red wait, cleanup/completion wake |
| 3 runner quota (A3:187) | Shared rate epochs/cooling, durable claims, immediate reset wake, runner+model revalidation |
| 4 Chrome/ChatGPT (A3:194) | Shared profile mutex alias plus browser pool and separate account quota; readiness/channel checks and restore at actuator |
| 5 renders (A3:200) | Hub render mutex, RAM preflight, PH pool, no outside-sandbox lock file |

Dependency completion is a scheduler eligibility event, not a fourth lease kind.
Browser login readiness, correct account, dirty worktrees and adequate memory
remain preflight obligations; a lease alone does not fix them.

## Phase C fixture boundary and remaining proof work

`tests/test_lease_scenarios.py` has one `backend` fixture factory. Replace its
returned class with an adapter around `lib/lease.py` wired to scratch storage,
fake hub time, fake liveness and a captured mailbox outbox. Preserve public
operations and observation methods in `tests/lease_model.py`; tests never mutate
model internals. `advance` changes only injected hub time; `tick` runs one due
maintenance pass; `restart` reconstructs the service over retained test storage;
failure arguments inject specific pre-ack boundaries. Production adapters must
exercise actual lease operations, not call this model to manufacture answers.

The model serializes operations and enumerates competing acquisition orders. It
does not prove thread/process linearizability, SQL syntax, network delivery, crash
durability, full approval authentication, provider fencing or actual migrations.
C must add PG concurrency/barrier tests, heartbeat-thread cleanup/context-exception
tests, outbox crash/dedup tests, CLI/HTTP parity, actor spoofing rejection, group-rate
retry reconciliation and the original A2 regression suite before any rollout.
