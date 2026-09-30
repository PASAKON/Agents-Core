# task-7656a701: W4.6a hub-side fixes from the W4.6 review

Branch `agent/developer-task-7656a701`, from `ac78e53d` (review task-79219f24). Developer worker, Sonnet 5.5.
No live system was contacted: no Infisical, GitHub, Tailscale or ssh. `deploy/join/*` and `tools/join_api.py`
(W4.6b) are untouched; `retire-setup` and the identity's access-token settings are untouched.

## Per-finding status

| Finding | Status | Where | Tests (functions in `test_w46a_hub_fixes.py`) |
|---|---|---|---|
| F1 approval gate | done | `lib/db.py` (`hosts.approved_at`, SQLite + Postgres, same migration loop as `deploy_pubkey`); `tools/hq_join.py` (`approve`, `node_status`, `provision` and `provision_pending` gate, `accept` resets `approved_at` and returns `fingerprint`); `runners/watchdog.py` (one line per host per hour) | 20 |
| F13 reserved names | done | `hq_join.reserved_hosts()` = `setup`, `org-node`, every key of `infisical_setup.MACHINES`; `_check_host` refuses with `bad_arg` for every verb | 3 (one parametrized over 5 names x 6 verbs) |
| F14 hq_root charset | done | `HQ_ROOT_CHARS_RE` `[A-Za-z0-9 ._/\\:-]+` in `_check_hq_root`; same rule in `lib.config._node_hq_root` | 3 (5 good + 19 hostile roots, accept and config parity), plus 15 new parity cases in `test_w44b_self_host.py` |
| F12 node.yaml vs path | done | `lib.config._node_yaml_host`: a declared host that disagrees with `_root_match_host()` raises `ValueError` naming both; a joined (undeclared) name is unaffected | 5, one with the real `_root_match_host` |
| F8 rotate block | done (see caveat 4) | `hq_join.rotate_scope`, `_print_rotate`, `_print_leave`; `infisical_setup.node_readable_secret_names(org)`; docs section "After a leave: rotate what the node could read" | 8: names path, documented fallback, lookup failure, partial leave, dry run, already-left, no value in output, doc check |
| F5 icacls | done, not run on Windows | `infisical_setup.lock_acl`, `_is_nt`, `_run_icacls`, `AclError`; `write_cred` locks the dir, then the `.tmp` file before `os.replace`; `cmd_save` turns `AclError` into an exit with "nothing saved" | 9: injected runner, exact argv, order, fail closed on dir and on file, missing icacls, no-op off Windows, stdlib-only |
| F4 (code part) | done | `NODE_SECRET_TTL = 90 * 86_400`; `mint_node_secret` sends `ttl 7776000`, `numUsesLimit 0` | 1 (plus the edited mint test in `test_w42_provision.py`) |

Not in this task: F2, F3, F6, F7, F9, F10, F11, F15 to F18 (W4.6b or CEO decisions).

## Decisions worth a look

- **`approve` compares what the operator read off the node, not what `status` shows.** The first draft of the
  mismatch message told the operator to re-read the value from `status`; that compares the hub with itself and
  defeats the gate. The message now points at the node's own screen and does not echo the stored fingerprint.
- **`provision_pending` returns `{host, skipped: "not_approved"}`, not an error.** An error would start the watchdog's
  one-hour failure back-off, so a host approved a minute later would still wait up to an hour. The "say so once"
  dict in the watchdog is separate from `_provision_retry_at` for the same reason. It is pruned when the host is no
  longer skipped.
- `approve` binds to the key it compared: the UPDATE has `status`, `pubkey` and `approved_at IS NULL` in its WHERE.
- `approve` normalises the fingerprint (strip, lower) and checks it against the bech32 alphabet before reading the row.

## Caveats and things to check

1. **`join.sh` / `join.ps1` do not print the fingerprint yet.** That is `deploy/join/*`, W4.6b. Until then the operator
   reads it on the node with `age-keygen -y <identity file> | tail -c 9`. The doc says so. Without that change the gate
   works but has nothing on the node's screen to compare with.
2. **The 8-character fingerprint is 40 bits** (2 key characters plus the 6 checksum characters), as specced. The doc
   states what it does and does not stop.
3. **F14 can lock out an existing node.** A `node.yaml` whose `hq_root` has `(`, `)`, `~` or Thai letters now makes
   `_node_hq_root` return None, so `self_host()` reports the host as unknown. No node has joined live yet (W4.x is
   built, not live), so nothing should break today; a Windows home like `C:\Users\x (2)\...` cannot join.
4. **F8 reads secret values into memory.** `GET /api/v3/secrets/raw` returns values; `node_readable_secret_names`
   keeps only `secretKey` and returns names, and a test proves no value reaches stdout or stderr. A newer Infisical
   API may accept a parameter that withholds values; I could not verify that without network, so it is not used. The
   lookup reads folder `/` only. If the lookup fails the block falls back to the documented categories and says so.
5. **F5 uses the literal `Administrators`** as the spec said. On a non-English Windows the group has another name;
   the SID form `*S-1-5-32-544` would not depend on the language. Not run on real Windows: only the argv and the
   fail-closed behaviour are proven. The ACL is set on the `.tmp` file before `os.replace`, so the secret is never in
   a file the inherited ACL allows others to read; the ACL moves with the file on a same-volume rename.
6. **F4 leaves a 90-day cliff.** A node's client secret expires 90 days after `provision`, and nothing re-provisions it.
   The doc gives the manual fix (leave, then mint, accept, approve, provision) and where the date comes from.
7. `leave mac|contabo|winbox` now returns `bad_arg` (reserved), not `not_joined`; tests updated. `not_joined` is still
   returned for a seeded, non-reserved row.
8. `accept()` returns one more key, `fingerprint`. `tools/join_api.py` is not edited; the full suite (which includes
   `test_w43_join_api.py`) passes, but W4.6b should decide whether `/accept` echoes it.
9. **Outside the declared test list:** `tests/test_self_host.py::test_node_yaml_wins_over_root_and_platform` broke
   under F12 (node.yaml `contabo` with ROOT at mac's path is now the error case). I changed ROOT to contabo's path
   and kept the assertion that node.yaml beats the platform source.
10. `tests/test_w44b_self_host.py` pins `_root_match_host` to "no match" in its autouse fixture; before this change the
    tests passed or failed depending on which machine ran them (the worktree root-matches `mac` on the Mac).
11. `_declared_hosts()` reads `config/hosts.yaml` again inside `_node_yaml_host`. `self_host()` is cached, so that is
    once per process.

## Tests

- New file `tests/test_w46a_hub_fixes.py`: 49 test functions, 103 cases per backend, each run on SQLite and Postgres.
- Touched: `tests/test_w41_hq_join.py`, `tests/test_w42_provision.py` (the `_join` helper approves by default,
  `approve=False` for gate tests; the mint test now expects ttl 7776000), `tests/test_w44b_self_host.py`,
  `tests/test_self_host.py`.
- Full suite, `python -m pytest -p no:warnings`: **5501 passed, 0 failed, 307 skipped** (7 min 52 s). The skips are the
  Postgres params, because `ORG_TEST_DB_URL` is unset in a default run.
- Postgres: a throwaway local Postgres 16 (Homebrew, `initdb` in the scratchpad, port 54329, database `org_test`,
  stopped afterwards) with `ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test` ran
  `test_w46a_hub_fixes.py`, `test_w41_hq_join.py`, `test_w42_provision.py`: **478 passed, 0 skipped, 0 failed**.
  The migration `ALTER TABLE ... ADD COLUMN approved_at`, `RETURNING` in `approve`, and the `DO UPDATE ... approved_at=NULL`
  reset all ran on Postgres.
- Scripts run as scripts: `scripts/test_org_tools_registry.py` ALL PASS, `scripts/test_mcp_role_config.py`
  OK, 0 failures, `scripts/test_tool_parity.py` ALL PASS.

## Commits

- `c7f31330` join: approval gate, reserved hosts, hq_root charset, node.yaml guard, 90d node secret, icacls, rotate block (W4.6a code)
- `56f860cd` tests+docs: W4.6a hub fixes (approval gate, reserved names, hq_root charset, node.yaml guard, icacls, rotate block, 90d ttl)
- the commit carrying this report

## Skill learning

- MISSING [no owner]: the pg param of the join tests is skipped in a default run (307 skips), so "all green" did not cover
  Postgres. Nothing says how to run it locally. A throwaway server takes one minute: `initdb -D <scratch> -U postgres
  --auth=trust`, `pg_ctl -o "-p 54329 -h 127.0.0.1"`, `createdb org_test`, then set `ORG_TEST_DB_URL`. Evidence: this task,
  478 passed on it. Worth a line in the tester playbook or the test docstrings.
- MISSING [no owner]: GateGuard in a parallel batch of Edits to one new path blocks only the first call; the others land.
  The first edit then arrives out of order and must be re-sent alone. Evidence: `docs/ops/hq-join.md`, this task (n=1).
- MISSING [no owner]: a brief that lists "touches" for tests misses the tests a rule change breaks. F12 broke
  `tests/test_self_host.py`, which was not on the list, and `test_w44b_self_host.py` depended on the machine it ran on.
  Finding them needed the full run of the join-related files, not the named ones. Evidence: this task, caveats 9 and 10.
