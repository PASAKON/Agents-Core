# Phase B — resource lease design summary

Order O-20261114-1701-56fb; task-dd492de4. Deliverables are a proposed design and
offline executable specification, not a rollout (`docs/design/resource-lease.md:3`).

## Decisions

- Use one Postgres-backed primitive for mutex, pool and rate; authoritative hub
  time, short TTL/heartbeat, hard max-hold, monotonic fencing and far-side cooling
  (`docs/design/resource-lease.md:22`). Keep durable dispatch claims until ack,
  with immediate mailbox wake through a transactional outbox; preserve FIFO within
  authenticated priority and exclude waiters from stale-task GC
  (`docs/design/resource-lease.md:146`).
- One proposed registry drives Python, CLI and Console HTTP. Paid resources fail
  closed; uncoordinated free work cannot claim a fenced lease. Registry examples
  stay inside the design, so no production config is changed
  (`docs/design/resource-lease.md:69`, `docs/design/resource-lease.md:118`).
- Specify the three tables/indexes and conditional SQL grant; all-or-none sorted
  groups prevent hold-and-wait. Migration freezes one authority at a time and has
  per-store rollback procedures (`docs/design/resource-lease.md:198`,
  `docs/design/resource-lease.md:372`). Add-a-system examples cover YouTube,
  Colab and the winbox screen (`docs/design/resource-lease.md:331`).
- Map every A2-001–012 defect and all A3 priorities; the legacy A2 tests remain
  Phase C acceptance work, not bugs fixed by this report
  (`docs/design/resource-lease.md:405`).

## Validation

Authored the 21 scenario tests before the model; final execution of
`/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_lease_scenarios.py`
passed **21 tests**. The executable range starts at
`tests/test_lease_scenarios.py:25` and ends with migration at
`tests/test_lease_scenarios.py:273`; Phase C swaps the backend factory at
`tests/test_lease_scenarios.py:13`. The model has injected time/liveness and
serialized transitions, not real concurrency (`tests/lease_model.py:1`).

## Open questions for the CEO

Nonblocking policy backlog for the rollout owner; no answer is required to finish B:
confirm initial paid bucket allowances, production maximum hold times, and which
resources require a card. The design disables unknown quota values and uses
explicitly illustrative limits (`docs/design/resource-lease.md:69`,
`docs/design/resource-lease.md:331`). Confirm whether any free advisory resource
should permit uncoordinated operation; exclusive resources default closed
(`docs/design/resource-lease.md:109`). No card or external command was sent.

## Not checked / risk

No live hub, provider, host-state or credential inspection was performed. Real
Postgres isolation, HTTP/CLI behavior, heartbeat threads, outbox recovery, physical
fencing and filesystem migration remain unproven; the required C checks are listed
at `docs/design/resource-lease.md:438`. Fencing requires actuator enforcement;
logical CEO override cannot guarantee an instantaneous physical stop
(`docs/design/resource-lease.md:56`). Legacy rollback may require stopping
admissions rather than restoring unsafe concurrency (`docs/design/resource-lease.md:389`).

## Skill learning

No skill file changed. Atomic file saving is not durable dispatch: keep a claim
through lookup, process death and delegate failure, then reclaim it on expiry;
the executable evidence is `tests/test_lease_scenarios.py:103` and the specified
integration is `docs/design/resource-lease.md:168`.
