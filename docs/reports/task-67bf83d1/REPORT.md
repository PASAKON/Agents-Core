# REPORT task-67bf83d1

W4.1 `tools/hq_join.py`: one-time join tokens, accept, leave plan, hosts export. Built and tested, **not live**: no Infisical, Tailscale, GitHub or ssh call exists anywhere in it, and nothing reads the export. Operator doc: `docs/ops/hq-join.md`.

## Summary

`tools/hq_join.py` has `mint`, `accept`, `leave [--live]` and `export-hosts`. Token consume is one `UPDATE ... RETURNING` in the same transaction as the `hosts` insert; 20 concurrent accepts give exactly 1 winner and 19 `already_used` on SQLite and on a local Postgres 16. `leave` goes through an injectable revoker table whose shipped default refuses every step, so `--live` cannot reach outside the hub until W4.2 and G3 supply real revokers.

## Files Changed

- `tools/hq_join.py` — new. Verbs, the `Step`/`Outcome`/`Revoker` interface, `UNWIRED_REVOKERS`, age-recipient checksum check.
- `lib/db.py` — `JOIN_TOKENS_SCHEMA` (run for SQLite and Postgres by `init_schema`), `_HOSTS_JOIN_MIGRATION` (`hosts.pubkey`, `hosts.config_json`), `_HOST_COLUMNS` extended, `seed_hosts_from_config` now also stores the whole hosts.yaml entry as `config_json`.
- `tests/test_w41_hq_join.py` — new. 54 tests x (sqlite, pg) = 108; the pg half runs only when `ORG_TEST_DB_URL` is set.
- `docs/ops/hq-join.md` — new. Verbs, the key-format justification, the revoker contract, the Run Inbox card line, open points.
- `docs/reports/task-67bf83d1/REPORT.md` — this file.

## Commits

- dc1ef2c9 — db: join_tokens table and hosts.pubkey/config_json for hq join (W4.1)
- 47d23fe9 — hq_join: one-time join tokens, leave plan, hosts export (W4.1)
- (this report, committed on top of the two above; its sha is in the submit_report call)

## Tests

- ran: `.venv/bin/python -m pytest -p no:warnings` (Core's venv; the worktree has no `.venv`), once, no `ORG_TEST_DB_URL`
  - passed: 4963
  - failed: 0
  - skipped: 82 (54 of them are the pg half of the new file)
- ran: `.venv/bin/python -m pytest -p no:warnings tests/test_w41_hq_join.py`
  - SQLite only: 54 passed, 54 skipped
  - With `ORG_TEST_DB_URL` on a **throwaway local Postgres 16** (initdb in the session scratchpad, TCP on 127.0.0.1 only, stopped afterwards; **not** the CTO's org_test): 108 passed, 0 failed
  - Race and probe tests repeated 8 times on both backends: 8 of 8 clean
- ran: `tests/test_db_hosts_letters.py tests/test_h1_node_probe.py tests/test_db_pg_translate.py tests/test_db_snapshot_fallback.py tests/test_db_backend_pg.py` with the same Postgres: 99 passed (207 together with the new file, 0 failed)
- ran: `scripts/test_org_tools_registry.py scripts/test_mcp_role_config.py` by path
  - passed: 23
  - failed: 12 (+1 error)
  - skipped: 0
  - **Identical on a clean detached worktree of `bacba144` (my base): 12 failed, 1 error, 23 passed.** Cause on both: `RuntimeError: tests must not touch a real checkout's tasks.db (ADR 0021)` at `lib/db.py`'s path guard, because these scripts use the default `DB_PATH` inside a worktree. Not caused by this change.

Guard probe, from `test_probe_a_read_then_write_consume_fails_the_single_winner_check`: with the atomic consume the 20 results are `{ok: 1, already_used: 19}`. With a read-then-write consume (barrier so all 20 read `unused` first) they are `{ok: 1, host_in_use: 19}`. The single-winner check therefore fails on the naive version, and only the `hosts` primary key stopped the other 19, which is why the check insists on `already_used` and not just "one winner".

## Issues / Blockers

- none blocking. Decisions and deviations are listed under Notes for Reviewer.

## Notes for Reviewer

1. **`lib/db_pg.py` not touched.** It was outside the declared touches and the self-repo-guard refused the edit; I did not work around it. The DDL is one constant in `lib/db.py`, executed for both backends by `init_schema`. The same loop adds the two `hosts` columns.
2. **`_HOSTS_MIGRATION` left as it was.** `tests/test_h1_node_probe.py::test_hosts_migration_list_names_exactly_the_new_columns` pins it to the three probe columns, and that file is not in my declared touches, so `pubkey` and `config_json` are in a second list, `_HOSTS_JOIN_MIGRATION`, run by the same loop.
3. **New `hosts.config_json` column.** `hosts` cannot rebuild a hosts.yaml entry (no `ssh`, `worktrees`, `chrome_device_id` and so on, and `runners` holds probe data). `config_json` holds the declared entry, filled by `seed_hosts_from_config` and by `accept`. Round trip is proven against the real `config/hosts.yaml` for mac, contabo, winbox: equal to `lib.config.hosts()`, key order included, and `lib.config` reads the exported file back identically.
4. **`export-hosts` writes to stdout by default** (`--out PATH` for a file). The task said "write hosts.yaml"; the tracked file has long hand-written comments that a dump cannot keep, so nothing overwrites it unless asked. Say if you want the default flipped.
5. **Name collision is stricter than the brief.** mint refuses any existing row that is not `left` (so `offline` and never-heartbeated NULL rows too), and any name declared in `config/hosts.yaml` even with no row. A sleeping host would otherwise be takeable by anyone holding a token.
6. **Key format: age X25519 recipient** (`age1...`, 62 chars, bech32 checksum verified), not `ssh-ed25519`. Reasoning in the doc: W4.2 seals the Infisical client secret to it, age is needed on both ends either way, and the checksum turns a typo into a refusal before the token is spent.
7. **`leave` refuses a host with no `pubkey`** (`not_joined`): mac, contabo, winbox were never joined through `accept`, and revoking "their" keys on every other host would cut the hub off. `leave` on an already-`left` host is a no-op with a note.
8. **Arguments are validated before the token is consumed**, so a bad `--pubkey` does not burn a token; a refusal after the consume (name taken in between) rolls the consume back.
9. **Token exposure, for W4.6:** the token is on stdout once and never in events, logs, the DB or this report (tests capture logging at DEBUG, stdout, stderr, events and tables). But a Run Inbox card stores its output on the hub and mails the finished card to the requesting session, so the token passes through both. It is single use and lives 15 minutes; still a departure from "a secret value never appears in a Run Inbox card". The card line is in the doc and was **not** dry-run here: `ask_run.py` refuses `--command` for a developer role (C-level only, or a committed `--script`).
10. **`accept` transport is W4.3's call.** A joining node has no `ORG_DB_URL` at join step 6, so a forced-command ssh key or a small endpoint has to carry the call.
11. **W4.2 must delete the node's sealed ciphertext on `leave`** when it adds that table; there is nothing to delete here yet.
12. `_platform_host()` in `lib/config.py` returns None when two hosts share an `os`; a joined node relies on `node.yaml` (join step 5). `lib/config.py` was not changed.
13. `plan_leave` lists every other host that is not `left`, including one that is still `pending_identity`; a real `authorized_keys` revoker must treat "no such line" as ok.
14. Untracked `.agy-run.log` in the worktree was there before I started and is not committed.

## Skill learning

- MISSING [Shared DEV Conventions §12 (shell scripts on this Mac)] : BSD `grep` has no `-P`; a scan written with it prints a usage error and, piped into `head`/`wc`, looks like an empty (clean) result. Use Python for the invisible-character scan · evidence: task-67bf83d1, first scan attempt
- MISSING [task brief | no owner] : `scripts/test_org_tools_registry.py` fails 12 + 1 error in any worktree (ADR 0021 guard), identical on clean HEAD, yet the brief tells the worker to run it. Say "baseline: 12 failed, 1 error in a worktree" so the worker does not spend a run proving it · evidence: task-67bf83d1, clean detached worktree of `bacba144`
- MISSING [task brief | no owner] : the brief's `.venv/bin/python` does not exist inside a worktree; the working interpreter is `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python` · evidence: task-67bf83d1
- MISSING [task brief | no owner] : declared touches omitted `tests/test_h1_node_probe.py`, which pins `lib.db._HOSTS_MIGRATION` to exactly the probe columns, and `lib/db_pg.py`; adding a `hosts` column or a PG table in this declared set forces a second migration list and a constant in `lib/db.py` · evidence: task-67bf83d1, `tests/test_h1_node_probe.py:311`
- MISSING [GateGuard fact protocol (user CLAUDE.md) | no owner] : Bash has a fourth variant, "Destructive command detected" (files modified, one-line rollback, verbatim instruction), fired on a command containing `rm -rf` of a scratch dir; the documented Bash gate is the two-fact one · evidence: task-67bf83d1, `initdb` into the scratchpad
