---
name: ALL_Procedure_UseALease
kind: procedure
description: 'PROCEDURE — Acquire, check and release an org resource lease. Trigger on /ALL_Procedure_UseALease and on "use a lease", "add a shared resource", "free a stuck lease". Do NOT replace the winbox desktop safety rules.'
owner: CTO
audience: [all]
created_by: agent
author: {role: developer, date: "2026-11-15"}
improved_by: []
aka: []
---

# Guard one shared operation with a lease

Input: resource name, purpose and authenticated session · Output: guarded work completed and lease released · Tool: `tools/lease.py`

Source check: 2026-11-15, task-5d88f72b, merged `lib/lease.py`,
`tools/lease.py`, `config/resources.yaml`, `lib/org_queue.py` and `lib/db.py`.
The HTTP details below are requirements from the task brief, not verified route code.

## Steps (numbered; each with the stop condition)

1. **Identify the shared thing before using it.** Use a lease for Chrome login,
   the winbox screen, GPU/render capacity, paid credits or API quota: mutex for
   exclusive use, pool for concurrent slots, rate for grants per time window.
   Check `config/resources.yaml` for an enabled matching resource and verified
   capacity. Stop if missing or disabled; a proposed row is not permission.
   For desktop safety also follow `.claude/skills/ALL_Rules_Winbox_PCLease/SKILL.md`;
   an org lease does not replace the CEO screen hold. No screen row is currently
   registered. `lib/org_queue.py` enables hub queue storage only when
   `ORG_QUEUE_HUB=1`; this does not enable resource leases. The legacy
   `acquire_lock(key: str, owner: str, ttl_seconds: int = 600) -> bool` in
   `lib/db.py` is an atomic owner/expiry lock, not the lease queue or fencing API.

2. **Add a resource with one YAML row plus a guarded call.** Use the existing
   registry schema; choose a unique name or pattern and a reviewed capacity
   (a rate needs grants and window seconds). Dynamic values come from
   `config/hosts.yaml` and `config/plans.yaml`. Missing references disable the
   resource. Defaults include heartbeat 5 seconds and fail-closed behavior.
   Stop if policy validation fails or an existing hub policy snapshot differs;
   changing that snapshot requires administrative migration.

   The real public signature in `lib/lease.py` is:

   ```python
   def lease(name,purpose="lease",wait_s=0,**kwargs):
       return lease_many([name],purpose=purpose,wait_s=wait_s,**kwargs)
   ```

   Keyword injection for tests/gateways is `service` and `actor` through
   `lease_many(names,purpose="lease",wait_s=0,*,service=None,actor=None)`.
   Production defaults require the trusted launcher to supply `LEASE_DB_URL`
   and `LEASE_OWNER_SESSION`. Never fabricate an identity or copy credentials.

   These three rows are copied verbatim from `config/resources.yaml`:

   ```yaml
   - {pattern: 'chrome:<host>:<port>', kind: mutex, capacity: 1, max_hold_s: 1800, enabled: false}
   - {pattern: 'host:<host>:workers', kind: pool, capacity_from: 'hosts.<host>.max_workers', max_hold_s: 3600}
   - {pattern: 'quota:<bucket>', kind: rate, rate_from: 'verified_quotas.<bucket>', paid: true, max_hold_s: 3600, enabled: false}
   ```

   Worked mutex example: `chrome:winbox:9224` represents one Chrome user.
   It currently refuses because the row is disabled. Only after reviewed
   activation does this guard a login operation:

   ```python
   from lib.lease import lease

   with lease("chrome:winbox:9224", purpose="Chrome login", wait_s=30) as held:
       held.assert_valid()
       # Perform the authorized login operation here.
   ```

   Worked pool example: `host:contabo:workers` consumes one slot from
   `hosts.contabo.max_workers`, not an invented fixed limit. A full pool waits.

   ```python
   with lease("host:contabo:workers", purpose="worker operation", wait_s=30) as held:
       held.assert_valid()
       # Keep the worker operation inside this context.
   ```

   Worked rate example: substitute a verified bucket for the pattern below.
   The row is disabled today; missing `verified_quotas` also disables it.
   After reviewed activation, one grant consumes quota for its rolling window;
   releasing does not refund it. Stop while waiting or cooling.

   ```python
   with lease("quota:<bucket>", purpose="authorized API operation", wait_s=30) as held:
       held.assert_valid()
       # Make one authorized provider operation here.
   ```

3. **Acquire, maintain authority, then release.** The Python context starts a
   heartbeat and releases on normal exit or exception. Call `held.assert_valid()`
   before each guarded side effect; stop on `LeaseLost` or any acquisition error.
   Heartbeats cannot extend past `max_hold_s`. A context that still waits after
   `wait_s` cancels its request and raises. For several resources declare one
   `lease_many` group; nested acquisition is rejected.

   Shell and PowerShell scripts call the same CLI from the repository root,
   using their configured Python interpreter. These are command templates:
   `REQUEST_ID` and `TOKEN` mean values returned by acquire, not literal values.

   ```text
   python tools/lease.py acquire host:contabo:workers --purpose "worker operation" --idempotency-key "task-operation-1"
   python tools/lease.py wait REQUEST_ID --wait-s 30
   python tools/lease.py status REQUEST_ID
   python tools/lease.py renew REQUEST_ID --token TOKEN
   python tools/lease.py release REQUEST_ID --token TOKEN
   ```

   Capture JSON and the exit code immediately (`$?` in shell, `$LASTEXITCODE`
   in PowerShell). Save `request_id` and the integer `token`; groups need the
   JSON object in `tokens` passed as one argument. Reuse an idempotency key only
   for the same operation. CLI calls have no background heartbeat: renew at
   the resource heartbeat interval while work runs, stop work if renewal fails,
   and release in shell cleanup or PowerShell `finally`. Never start work on
   a waiting response. Argparse usage errors can print usage instead of JSON.

   | Exit | Meaning | Action |
   |---|---|---|
   | 0 | Granted or success | Inspect the result and proceed only with live authority |
   | 2 | Invalid arguments/configuration | Fix input; do not perform shared work |
   | 3 | Waiting/awaiting approval | Retain request ID; wait, do not acquire repeatedly |
   | 4 | Refused, stale, expired or terminal | Stop guarded work |
   | 5 | Hub unavailable | Stop; do not bypass coordination |

4. **Use the Console gateway on hosts without DB credentials.** The task brief
   specifies HTTP routes `/api/leases/acquire`, `/api/leases/renew`,
   `/api/leases/release`, `/api/leases/wait`, `/api/leases/status`, off unless
   `LEASE_CLI` is set. These are HTTP endpoints, not repository paths.
   The referenced design document and Console implementation are absent from
   this checkout as of 2026-11-15. Stop integration until the Console owner
   supplies the verified methods, authentication and payload contract; do not
   infer them from CLI flags or assume the routes are enabled. Use that
   authenticated gateway once verified instead of installing DB credentials.

5. **Read status before recovery.** Use the status command above with the same
   owner session. Read `state`, `reason`, `position`, `expires_at`, `token` and
   `tokens`; `position` may be null, and expiry is hub time. Status is read-only
   and neither renews nor claims a lease. Another session receives `not_owner`.
   Stop if expired/refused; a stale token is never authority.

6. **Free a stuck lease through its owner or an authenticated administrator.**
   The owner releases with the matching current token. Expiry and confirmed
   death are reaped by the service; quiet is alive and unknown liveness waits
   for TTL. Stop before trying to evict a live peer yourself.
   In `lib/lease.py`, `Service.administer("release_override", actor,
   request_id=request_id, reason=reason)` permits only authenticated CEO or CTO
   actors with a nonempty reason. The trusted administrative caller supplies
   that actor; the CLI exposes no administrative subcommand or role flag.
   It removes holders, marks waiters done, schedules successors and records
   `release_override` in `lease_events`, including actor, role, reason, owner
   and stop intent, with durable outbox delivery. CEO-only `override` is a
   separate takeover operation. Do not delete hub rows to free a lease.

## Verify (the command, and what "done" looks like)

Use `python tools/lease.py status REQUEST_ID` as the owning session after release.
Done means guarded work has stopped, release succeeded and status is terminal
(`done`, exit 4), not a reusable grant. For documentation validation, run
`python -m pytest tests/test_skill_use_a_lease.py`; all tests must pass offline.

## Failure modes seen (dated)

- 2026-11-15 source check: mutex/rate example rows are disabled; these are
  activation examples, not claims of deployed capacity (`config/resources.yaml`).
- 2026-11-15 source check: paid resources must fail closed; `validate_policy`
  rejects paid uncoordinated policies. Hub-down results or exceptions stop work;
  `MemoryStore` is a test fake, never a production fallback (`lib/lease.py`).
- 2026-11-15 source check: Console HTTP contract cannot be verified in this
  checkout; the task brief alone is insufficient for executable HTTP examples.

## Field notes
