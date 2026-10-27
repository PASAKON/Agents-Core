# REPORT task-503505d8

COO audit log (#38) and field-note path (#24b) through `coo_gate`. Built and tested on SQLite; **the Postgres trigger has not been run against a live hub** (see Not checked). **Not pushed, no PR yet**: see Blockers.

## Summary

Two new gate ops, `audit_append` and `field_note`, write taskless `coo_audit` / `coo_field_note` events as actor `coo_gate`. `org_coo_role.sql` accepts exactly those two kinds with exact payload keys and types, and its section 6 now proves a valid row is accepted and a wrong-actor or wrong-shape row is refused. `scripts/coo-audit-hook.py` feeds the audit op from a PostToolUse hook (fail open, 2 s). `tools/coo_field_notes.py list` is the reader for the CTO/PH. No grant changed, the `want` privilege list is unchanged.

## What was built

| Piece | Where |
|---|---|
| `audit_append {op, session_id, tool, input, ok}`: strict key set, `_coo_session` check, cap 600 rows per session per hour, payload `{session_id, tool<=100, input<=2000 redacted, ok}` | `runners/coo_gate.py` |
| `field_note {op, session_id, skill, tag, text}`: skill regex `^[A-Za-z0-9_.-]{3,80}$` (fullmatch) and a directory under `.claude/skills/`, tag in MISSING/WRONG/COSTLY/CONFIRMED, text one line <=600 | `runners/coo_gate.py` |
| MCP tool `field_note(skill, tag, text)` and `TOOL_NAMES` | `runners/coo_mcp_server.py` |
| Trigger blocks for both kinds (task_id NULL, actor `coo_gate`, `jsonb_typeof` per key, COALESCE'd lengths) and a section 6 proof loop | `deploy/coo-gate/org_coo_role.sql` |
| PostToolUse hook, stdlib only, exit 0 and no output on every path, 2 s total budget (socket deadline plus a SIGALRM backstop), session id `CXO_SESSION_ID` else the hook's `session_id`. **Not registered anywhere** (`git grep coo-audit-hook` finds only the file and its tests) | `scripts/coo-audit-hook.py` |
| Reader `list [--since ISO]`, prints `skill · tag · ts · text` oldest first | `tools/coo_field_notes.py` |
| One README section: what it does, how the PH wires it, the limits | `deploy/coo-gate/README.md` |

## Decisions that differ from, or go beyond, the brief

1. **Redact, then cut (the brief said cut, then redact).** With the brief's order a secret straddling character 2000 is cut in half and the left half can be shorter than the length rule, so it is stored. `test_audit_cuts_to_2000_and_a_secret_on_the_cut_does_not_leak` fails when the order is swapped (mutation run below). The stored text is still <= 2000 characters.
2. **The 600/hour cap is counted in the gate's memory, not in the hub.** `org_coo` may not SELECT audit rows (and "do not change grants"), so a count query would need a new grant. The cost: a gate restart resets the counter. Stated in the README. The same helper caps field notes at **30/hour** (my addition: otherwise the COO could write unbounded 600-character rows).
3. **Redaction helper.** `lib/` has only `db.redact_url` (URL passwords); I reuse it, and reuse `tools/ask_run`'s existing secret shapes (`SECRET_KEY_WORDS`, `PRIVATE_KEY_MARKER`, `_TOKEN_SHAPES`, a private name) instead of a second copy, plus Basic and `ya29.` shapes, `key=value` for secret-named keys (a bare `$ENV` reference is kept), and a mask for unbroken >=32-character letter+digit runs (paths after `/` and UUIDs are kept). It is linear time: a first version took 5.2 s on 64 KB of `token=` repeated and is now 0.02 s (the gate serves one request at a time).
4. **Also done, small:** NUL and lone surrogates are stripped before the write (Postgres refuses both in a jsonb string, which would have let any command containing one skip the log); the field-note text is redacted too (notes end up in skill files in a public repo); the reader replaces control characters (the COO writes the text, a CTO reads it in a terminal); a tool name over 100 characters is cut, not refused.
5. `field_note` sits before `respawn_clevel` in `TOOL_NAMES` so the existing assertion `TOOL_NAMES[-1] == "respawn_clevel"` stays true. No existing test was edited.

## Roll-out order (for the PH)

1. Re-run the grants step: `org_coo_role.py --grants-only` (README step 1). It installs the new trigger and runs section 6; **read its output**, it is the first time this SQL meets a real Postgres.
2. Restart `org-coo-gate` (read the tmux/cgroup warning in CLAUDE.md first). Until then the running gate answers `unknown op`.
3. Wire `python3 <root>/scripts/coo-audit-hook.py` under `hooks.PostToolUse` (and `PostToolUseFailure` if failed calls should show `ok: false`) in SomPong's settings. The launcher must export `CXO_SESSION_ID`: the hook's own `session_id` is a Claude id, not a hub session, and the gate refuses it.

## Limits (also in the README)

- The hook is fed from SomPong's own settings, so the COO can stop feeding it. It cannot change or delete what was written, as `org_coo`: INSERT only, no SELECT of these rows. Root on the box can.
- Redaction is by shape: a secret in no known shape (bare password, `curl -u user:pass`) is stored; a git SHA is masked like a key.
- Over the cap, rows are dropped; only the gate's journal says so.
- Every tool call now costs one subprocess start plus one gate round trip (worst case 2 s if the gate hangs).

## Not covered by the brief, flagged

`tests/test_coo_gate.py::test_coo_ask_run_hub_error_comes_back_as_ok_false` fails inside a worker session because `WORKER_TASK_ID` is set (`ask_run` refuses role `coo`). It passes with `env -u WORKER_TASK_ID`. The cause is the environment, not this change; I did not edit that test.
