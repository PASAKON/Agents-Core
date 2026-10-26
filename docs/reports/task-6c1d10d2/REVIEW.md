# Re-review of d6ef52d9

**Verdict: changes-needed.** Scope: the single commit `git diff 39378664 d6ef52d9`. All implementation file:line references below refer to **d6ef52d9**, not the checkout at f88af2ed. No implementation files were edited.

## Required changes

1. **P2 — Reject malformed UUID lock contents before allowing a launch.** `runners/coo_dispatch.py:499` accepts arbitrary bytes as role UUIDs, and `:500` silently discards empty contents. A surviving Claude with a valid `--session-id` then fails the comparison at `:513` if its role lock has garbage or is empty, and the function returns `None` at `:525`. With the wrapper gone, a fresh empty publisher snapshot and no role-named tmux session, this restores the duplicate-launch gap. A synthetic proc probe returned `process_role_alive` for the correct UUID, but `None` for both `garbage` and an empty lock. Validate every matching lock as a UUID and refuse on invalid/empty contents; add regressions for those cases. Unreadable files already fail closed through the OSError handler at `:522`–`:524` (confirmed with PermissionError). Missing identity records remain a limitation of this mechanism, which is not a general environment-marker scan.

2. **P2 — Do not accept failure to assume org_coo as proof of an INSERT refusal.** `deploy/coo-gate/org_coo_role.sql:208` executes `SET LOCAL ROLE` inside the same protected body whose handler at `:218` swallows `insufficient_privilege`. A denied role switch itself raises that condition, so both proof iterations can pass without attempting either INSERT. The new comment at `:216`–`:217` claims the opposite. Separate role-switch success from the expected INSERT failure, or track successful role assumption and rethrow errors before that point, while preserving rollback of the role and test row. This is a proof-integrity defect, not evidence that org_coo can insert done events in a correctly deployed database. PostgreSQL's [SET ROLE implementation](https://github.com/postgres/postgres/blob/master/src/backend/commands/variable.c) explicitly sets `ERRCODE_INSUFFICIENT_PRIVILEGE` when the session user cannot assume the role.

## Requested checks

### 1. Exception text in done events

Fixed: `runners/coo_dispatch.py:434`–`:436` logs the OSError privately and returns exactly `tmux_start_error:<class>`. Nonzero tmux stderr is also only logged (`:437`–`:439`). The return reaches `_respawn_done` through `:644`–`:653`; a direct mocked probe through `_respawn_checked` and the real completion builder produced `reason=tmux_start_error:OSError`, `started=false`, without the injected `password=REVIEW_FAKE` in the event.

No other arbitrary backend exception-message sink was found in `coo_respawn_done`: process, reservation, outer check and live-session failures use fixed categories plus class names (`:524`, `:534`, `:540`, `:546`, `:552`, `:564`, `:590`). The remaining `str(e)` at `:469` is the deliberately generated policy refusal from `lib/coo_policy.py:58`–`:67`, not backend exception text. The new test at `tests/test_coo_dispatch.py:457` tests the start helper only; it would be stronger to retain an event-level regression like the review probe.

### 2. Budget accounting and COO caller authority

The requested accounting is correct for dispatcher-authored completions. `lib/coo_policy.py:104`–`:115` identifies settled request IDs; `:132` skips `started:false` completions and `:134` skips their original requests. Pending requests remain counted. A legacy completion lacking `started` uses `ok` at `:132`, so `ok:true` counts once at its completion timestamp. Explicit `started:false` overrides even `ok:true`. Role-window and global Bangkok-day checks are at `:136`–`:148`; invalid/future times count conservatively.

The gate reads **both** kinds with their `kind` field (`runners/coo_gate.py:234`–`:239`), as supplied by `deploy/coo-gate/org_coo_role.sql:98`–`:101`. It therefore applies the same settlement rules, rather than treating done rows as additional requests. Concurrent gate requests can overqueue, but dispatcher role/global flocks remain held through the completion write (`runners/coo_dispatch.py:528`–`:560`), and it rechecks all done events plus prior requests (`:569`–`:577`). No COO-side bypass of three starts per Thai day or one per role per ten minutes was found through this change, assuming the installed guards and durable dispatcher completions.

A forged `started:false` completion would release a pending reservation if fed directly to the policy; the policy trusts event provenance. It does not remove an independently recorded `started:true` completion. org_coo cannot forge done rows: the request-only special case ends at `org_coo_role.sql:154`, and the event-kind allowlist rejects `coo_respawn_done` at `:155`–`:156`; the trigger is installed at `:184`–`:186`. The SELECT grant on the view does not grant writes. Direct policy probes confirmed refused requests use no budget, pending requests block within ten minutes, legacy successes count, and three successful starts block a fourth role.

### 3. Lock file uncertainty and stale identity

Unreadable lock: fail-closed, returning `proc_read_error:<class>`. Garbage or empty lock: **not fail-closed**, as finding 1 demonstrates. A stale valid UUID alone does not refuse: a live non-tmux process must also advertise it in a separate `--session-id` argument (`runners/coo_dispatch.py:511`–`:515`). A reused UUID or an unrelated process advertising that UUID can therefore cause a false refusal. That conservative availability cost is acceptable as fail-closed behavior; deleting stale locks without establishing that no matching live session remains would weaken the safety guarantee. The README now accurately describes cmdline/comm inspection and the lack of manual-launcher participation (`deploy/coo-gate/README.md:46` onward).

### 4. SQL error conditions

The selected conditions are correct for the two intended cases: a plain guard-trigger `RAISE EXCEPTION` uses `raise_exception` / P0001, and a missing INSERT privilege uses `insufficient_privilege` / 42501. See PostgreSQL's [RAISE documentation](https://www.postgresql.org/docs/current/plpgsql-errors-and-messages.html) and [error-code table](https://www.postgresql.org/docs/12/errcodes-appendix.html). Unrelated conditions such as an undefined table now propagate. Successful forbidden INSERT still raises the distinct ZX001 at `org_coo_role.sql:213`, rolling back the subtransaction and setting `accepted=true` at `:215`, then failing the proof at `:221`. However, condition narrowing alone does not identify which statement raised 42501; finding 2 remains.

## Validation and limits

Reviewed the exact target in a temporary archive inside the assigned worktree. Ran the four COO/launcher/resolver test files; results and environment details are recorded in REPORT.md. Scoped `git diff --check` and `bash -n` for both shell scripts passed. Additional isolated Python probes exercised UUID corruption/unreadability, policy settlement/legacy accounting, and the tmux exception through completion construction. No live database proof, hub, service, tmux session or Claude process was started; SQL conclusions are static analysis checked against PostgreSQL documentation/source.
