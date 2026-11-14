# REPORT task-c59484f3

## Changes

- `tools/chatgpt_images.py`: opt-in lease around the complete run, before CDP attach, including recovery and browser close. `--wait-s` defaults to 600. Acquires ChatGPT rate and home mutex together through `lease_many`, because a rate resource alone does not serialize active runs. Checks authority before attach and scheduler advances. Unset `LEASE_DB_URL` prints exactly `lease: off (LEASE_DB_URL unset)` and follows the old runner path.
- Quota exit 5 reports cooling before release. Parses explicit ISO timestamps, relative hours/minutes, and clock times including AM/PM; unknown text falls back to two hours. Preserves more provider hazard text for parsing.
- `--lease-host` identifies the canonical CDP host; loopback URLs require it or `ORG_HOST`. A forwarded CDP endpoint must use the actual browser host, not the forwarding host.
- `tools/home_lock.py`: existing transport boundary delegates to lib.lease when enabled; existing Console HTTP transport remains unchanged when unset. Preserves CLI verbs, output shape, Python context API, TTL argument validation and exit codes 0/2/3. Uses trusted `LEASE_OWNER_SESSION`; does not promote a caller-supplied owner to another identity. Reads durable holder records so separate CLI invocations can renew/release.
- `lib/lease.py`: adds live-holder snapshots, optional policy-bounded TTL renewal for compatibility clients, and current-holder-authorized rate cooling. Cooling can only extend a held rate resource; no administrative role spoofing or reset privilege is introduced.
- `config/resources.yaml`: disabled ChatGPT rate reference and disabled home mutex. No reviewed ChatGPT grants/window or per-port home policy exists in `plans.yaml`/`hosts.yaml`, so no entitlement was invented or enabled.
- `tests/test_chatgpt_lease.py`, `tests/test_home_lock_lease.py`: fake-store/fake-browser integration coverage for contention, release, timeout cancellation, cooling/deadline/fallback, owner authorization, CLI contract, expiry, exceptions and unset-variable fallback.

The supplied read-only design still aliases ChatGPT to Chrome, whereas this task explicitly requests a ChatGPT rate row. This implementation follows the task, with an atomic home mutex in the same group to retain serialization. It does not change the Console route or migrate existing holders.

## Validation

Used `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`, without org wrappers or a real hub/Chrome.

- `python -m pytest tests/test_chatgpt_lease.py tests/test_home_lock_lease.py tests/test_lease_scenarios.py`: **64 passed**.
- `python -m pytest tests/test_chatgpt_images.py`: **74 passed**.
- Initial combined run also included `tests/test_home_lock.py`: **135 passed, 6 setup errors** before the final additional tests. All six errors came from its existing `ThreadingHTTPServer` fixture: sandbox socket creation raises `PermissionError: [Errno 1] Operation not permitted`. No test assertion failed. The new home-lock suite uses mocked HTTP responses and passes without sockets.
- `git diff --check`: passed.
- MAILBOX.md was absent at each checkpoint. No git add/commit, service sign-in, external messages, real database connection or browser interaction performed.

## Blockers

- Existing socket-based home-lock tests require a review environment that allows a local test HTTP server. Approval escalation is unavailable in this sandbox; no production service was used as a substitute.

## Not checked / risk

- No real PostgreSQL or browser integration was run. Fake transactions exercise the production Service scheduler, but do not prove SQL concurrency or browser actuator fencing.
- Both new resource rows remain disabled. Before enabling, provide reviewed settings, reconcile live Console holders, and switch all writers together in C3. Mixed legacy Console and lease writers are not mutually exclusive.
- CLI ownership is bound to `LEASE_OWNER_SESSION`. `--owner` for a different session is refused with exit 3 in lease mode; legacy Console authorization is unchanged.
- TTL renewal is capped by the lease resource's `max_hold_s`. The disabled home proposal currently inherits a 1800-second maximum; a future enabled policy must explicitly reconcile that cap with callers requesting up to six hours or repeated renewals.
- Bare clock reset text assumes the runner's local timezone matches the browser's displayed timezone; explicit ISO offsets are respected. Remote-browser timezone differences and unfamiliar localized reset wording need deployment verification. Unknown wording uses the two-hour fallback.
- The lease maximum hold remains authoritative: a job exceeding it stops when validity is checked. Browser operations already in progress cannot be atomically fenced by this library alone.
- Cooling persistence requires the lease store to remain reachable. A failure is logged by the runner; server expiry is still the library's fallback when release cannot reach storage.

## Skill learning

- Rate admission and active-holder exclusion are separate: production Service permits multiple live rate holders within the grant budget. The concurrent-run test proves that grouping the rate grant with the home mutex blocks the second browser attach until release.
- Existing Console wrapper tests depend on local sockets; the new fake transport test verifies the unchanged request URL/body without requiring a listening server.
