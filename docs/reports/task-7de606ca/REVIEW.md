# PR #449 re-review — 39378664

**Verdict: changes-needed.** Review scope: `git diff 729fa0a2 39378664 -- deploy lib runners scripts tests`. The main integration at `ddfdca2c` is excluded. All implementation line references refer to **39378664**, not the checkout. No implementation files were edited.

## Previous findings

| Finding | Status | Evidence at reviewed head |
| --- | --- | --- |
| 1. Fail-closed singleton | **partially** | `runners/coo_dispatch.py:475` rejects missing, erroneous, invalid, future or older-than-180-second host publications. `:489` checks local launcher argv. Role/global reservations at `:518` remain held through the completion write. These fix the ordinary launcher case; argv-only detection is narrower than the specified environment-marker check (see below). |
| 2. Clock rollback / delayed launches | **fixed** for the reported timing defects | `lib/coo_policy.py:130` counts invalid/future timestamps as recent; `:128` replaces a successfully completed request with its completion timestamp. `runners/coo_dispatch.py:559` includes completion events, and `:533` serializes across roles. The daily cap is now global. Refused-request accounting introduces the availability issue below. |
| 3. Backend error disclosure | **partially** | `scripts/resolve-resume-id.sh:36` extracts only the prescribed exception-class pattern and `:47` emits a fixed category. `runners/coo_dispatch.py:580` and `:554` no longer expose backend exception messages. However, `:435` still interpolates an `OSError` into the completion reason. |
| 4. SQL null role | **fixed** | `deploy/coo-gate/org_coo_role.sql:145` requires string types and a null-safe role allowlist; `:147` applies the same protections to host, and `:149` requires a string by_session. The proof attempts both forbidden inserts at `:203`. Live PostgreSQL deployment was not exercised. |

## Required changes

1. **P2 — Remove the remaining exception-message completion path.** `runners/coo_dispatch.py:434` catches `OSError` and returns its full text at `:435`; `_respawn_checked` forwards that reason to `_respawn_done` at `:634`–`:643`. The outer exception sanitizer never sees it because it is returned normally. A mock `subprocess.run` raising `OSError('password=REVIEW_FAKE')` produced `(False, 'tmux could not start cto-1234abcd: password=REVIEW_FAKE')`. This is an existing path left uncovered by the fix, not a newly added exception interpolation. Ordinary exec failures usually contain executable/path details, rather than a database password; the probe establishes the unfiltered sink, not a demonstrated production credential disclosure. Return a fixed reason plus class name and keep details in private logs. Add a regression for this path through the completion event.

2. **P2 — Separate failed attempts from the global start budget.** `lib/coo_policy.py:126` discards unsuccessful completion events but leaves their original requests counted at `:135`. Only successful starts deduplicate requests (`:109`, `:128`). Three accepted requests for different roles during a transient publisher failure, or while those roles are already running, consume the entire Bangkok-day budget even though no process starts. Later a genuinely dead fourth role cannot recover. A direct policy probe with three request/`started:false` pairs and zero starts returned `globally already has 3 respawns today`. This is an avoidable self-DoS under the fix specification's **three starts/day** policy. Gate-level refusals before insertion do not count (`runners/coo_gate.py:239`–`:243`); dispatcher refusals do. Retain separate attempt throttling if desired, reserve pending starts atomically, release reservations on definitive pre-launch refusal, and count durable starts for the daily start cap. Preserve fail-closed handling of uncertain launch outcomes.

3. **Resolve the remaining singleton coverage gap or explicitly narrow the contract.** The new argv scan detects the supported long-lived wrapper (`scripts/cxo-claude.sh:924` runs Claude as a child), including wrappers in nonstandard tmux sessions. However, a Claude process surviving its wrapper's death has no `cxo-claude.sh --role ...` argv, even though it retains role/session environment markers. With a nonstandard tmux name and a fresh empty publisher snapshot, this process still escapes all these checks. The original fix specification explicitly covered marker-bearing processes. Add reliable coverage for surviving children (for example a tracked process group/cgroup), or document and justify the narrower wrapper-only guarantee before marking finding 1 fully fixed. The reservation serializes COO dispatchers; external/manual launchers do not acquire it, so it is not a universal lifetime singleton lock.

## Requested edge checks

### (a) argv-only process detection and tmux exclusion

`runners/coo_dispatch.py:498` reads comm/cmdline, never environ. Script matching uses an entire NUL-delimited argument's basename, followed by an exact `--role`/role pair (`:506`–`:510`). A project-head lane mentioning CTO is not a CTO launcher. The `comm.startswith(b"tmux")` exclusion at `:504` avoids treating the shared server's historical command arguments as a live role. Reads fail closed unless the PID directory has disappeared (`:500`). This is reasonable for normal wrappers, with the surviving-child limitation above. The prefix exclusion is broader than an executable-identity check, so it is not a defense against a process deliberately disguising its comm. The README still incorrectly promises an environ scan (`deploy/coo-gate/README.md:46`); update it to match the final mechanism.

### (b) fresh-launch tmux rename

`scripts/cxo-claude.sh:392`–`:402` renames only when minting a fresh SID inside tmux. Explicit session overrides, resume UUIDs, inherited IDs and already-valid tmux suffixes bypass it. Arguments are quoted and the new name uses the validated role plus generated hex ID. An exact destination existence check avoids knowingly colliding; tmux itself handles a race by refusing rename. Failure/collision warns and continues, so rename is best-effort identity hygiene, not a singleton guarantee. It also renames a non-role-named containing session, potentially affecting its other panes; no code execution injection was found. This change exceeds the original fix-spec constraint against further launcher edits, but is explicitly in this re-review's scope.

### (c) SQL subtransaction and SET LOCAL ROLE

The block at `deploy/coo-gate/org_coo_role.sql:205` always exits its inner protected body through an exception: either INSERT fails, or the explicit `ZX001` at `:211` fires. Both paths roll back the inner subtransaction, including `SET LOCAL ROLE` and any inserted row. The handler sets the PL/pgSQL variable `accepted`, and the outer block raises if an insert succeeded. Consequently **this block cannot retain its changed role or commit the test row** through the shown paths. A successful subtransaction exit would NOT by itself reset SET LOCAL; it normally lasts to the outer transaction end. Here the forced rollback is the crucial distinction.

This interpretation follows PostgreSQL's [SET rollback semantics](https://www.postgresql.org/docs/current/sql-set.html) and [PL/pgSQL exception rollback rules](https://www.postgresql.org/docs/current/plpgsql-control-structures.html#PLPGSQL-ERROR-TRAPPING). Sequence allocation can still advance despite row rollback. Proof strength is limited: `WHEN OTHERS THEN NULL` also accepts unrelated errors (including failure to assume the role), so this is not independently conclusive proof that the intended trigger rejected each row. Narrow expected exceptions and verify the effective role for stronger deployment validation. Current Python coverage checks SQL text, not execution.

### (d) new exception leaks

The newly added host/proc/reservation/catch-all paths expose fixed categories and exception class names. The live_sessions path and nonzero tmux stderr path are sanitized. The remaining OSError return is detailed in required change 1. The `str(e)` policy refusal at `runners/coo_dispatch.py:468` is a policy-generated input rejection, not arbitrary backend exception text.

### (e) refused requests and 3/day

Conservative attempt counting does enforce an upper bound on starts, but it is not equivalent to the agreed start quota and can disable all recovery after three harmless refusals. Treat this as changes-needed unless an explicit product decision replaces the start quota with an attempt quota and accepts that availability cost. See required change 2.

## Validation

- Reviewed an archived copy of exactly `39378664` within the assigned worktree; checkout/branch unchanged.
- Ran the four specified COO/launcher/resolver test files; result recorded in REPORT.md.
- `bash -n` on both changed shell scripts and scoped `git diff --check 729fa0a2 39378664` passed.
- Direct synthetic probes reproduced the residual OSError disclosure and global quota exhaustion with zero starts.
- No live hub, deployed PostgreSQL proof, dispatcher service, tmux/Claude launch, or external service mutation was performed. SQL conclusions are static analysis corroborated by official PostgreSQL documentation.
