# Review task-65fce92c

**Verdict: approve.** Reviewed only `git diff d6ef52d9 b4735822`; both required changes are resolved. No regressions found in scope.

- `process_role_refusal`: every readable matching lock is checked after whitespace/case normalization. Empty or malformed contents return `lock_uuid_invalid`, including alongside a valid lock. Canonical UUIDs still work; unreadable locks retain the fail-closed OSError path. Invalid stale locks now block launches intentionally.
- SQL proof: `switched` starts false each iteration and becomes true only after successful role assumption, verified through `current_user`. A denied switch therefore rethrows. PL/pgSQL variables retain their values across exception rollback, so an INSERT refusal sees true ([PostgreSQL](https://www.postgresql.org/docs/current/plpgsql-control-structures.html#PLPGSQL-ERROR-TRAPPING)).
- Every path either raises an INSERT error, forces ZX001 after successful insertion, or propagates another error. Consequently the test row and local role change roll back; ZX001 still fails the proof afterward. SET LOCAL is undone by rollback ([SET semantics](https://www.postgresql.org/docs/current/sql-set.html)). Bare `RAISE;` inside this handler correctly rethrows the original exception; the same handler does not catch it again ([RAISE semantics](https://www.postgresql.org/docs/current/plpgsql-errors-and-messages.html)).

Validation: isolated target-code UUID probes and scoped diff whitespace check passed. Dispatcher pytest could not run because pytest is absent; SQL conclusions are documentation-backed static analysis, without a live database run.
