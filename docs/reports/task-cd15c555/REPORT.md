# task-cd15c555: Org Mesh W4.2, per-node identity sealed to the node's age key

## Summary
A `pending_identity` host is now provisioned by one Mac-side call
(`python -m tools.hq_join provision --host <name>`): a client secret minted under
the shared identity `org-node`, sealed to the host's age recipient, the host's GitHub
deploy key registered, only the ciphertext stored, ids kept for revoke, row moved to
`identity_ready`. `leave --live` revokes exactly that host's client secret and deploy
key by the stored ids. Nothing live is touched: every outside call is injected in the
tests, and the live path is off unless `ORG_W42_PROVISION=1` on the admin host.

## Files Changed
- `lib/sealed.py` (new) — `seal(recipient, bytes) -> armored bytes`, `open(identity_path, armored) -> bytes`, `SealError`. Plaintext on stdin, result on stdout, never argv or a temp file. Recipient checked with `hq_join.valid_age_recipient`. Missing `age` raises `SealError` (no fallback). Binary path and runner injectable.
- `tools/infisical_setup.py` — stdlib-only additions: `ensure_node_identity`, `mint_node_secret`, `revoke_node_secret`, `list_node_secrets`, `IdentityCapError`, `node-secrets` verb (lists description/id/created/revoked, never a value). `reconcile()` now builds identities through a shared `_create_identity`.
- `lib/db.py` — table `node_secrets` (`NODE_SECRETS_SCHEMA`, one DDL string for SQLite and Postgres); `hosts.deploy_pubkey` through `_HOSTS_JOIN_MIGRATION`.
- `tools/hq_join.py` — `accept --deploy-pubkey`; verbs `provision` and `sealed`; `provision()`, `provision_pending()`, `sealed_ciphertext()`; wired revokers for `infisical_client_secret` and `github_deploy_key`; `default_revokers()`; gh deploy-key add/delete through an injectable runner.
- `runners/watchdog.py` — `_provision_identities()` (one small function) plus one try/except call in `scan_once()` after the letter retry.
- `docs/ops/hq-join.md` — provision flow, env flag, what leave revokes, the 5-identity rule, schema, what is left.
- `tests/test_w42_sealed.py` (new), `tests/test_w42_provision.py` (new).
- `docs/reports/task-cd15c555/REPORT.md` — this file.

## Commits
- 10a59ed1 — w42: sealed age helper, org-node secrets, provision/sealed verbs, wired revokers
- a80441d2 — w42: watchdog identity pass, sealed + provision tests (fake org/gh/age, sqlite+pg)
- (final) — w42: docs/ops/hq-join.md, report (sha in `git log`)

## Tests
- ran: `ORG_TEST_DB_URL=postgresql://orgtest@127.0.0.1:55432/org_test .venv/bin/python -m pytest -p no:warnings` (whole suite, once, against a throwaway local Postgres 16 started for this run in the session scratchpad and stopped afterwards; never a real hub)
- passed: 5204
- failed: 0
- skipped: 7
- New files alone, SQLite only (no `ORG_TEST_DB_URL`): `tests/test_w42_provision.py` 73 passed + 73 skipped (the `pg` param), `tests/test_w42_sealed.py` 19 passed. With Postgres: `test_w42_provision` + `test_w42_sealed` + `test_w41_hq_join` = 273 passed, 0 skipped.
- `scripts/test_org_tools_registry.py` ALL PASS; `scripts/test_mcp_role_config.py` OK, 0 failures; `scripts/test_tool_parity.py` ALL PASS.
- `test_real_age_round_trip` RAN and passed: `age` v1.3.2 is at `/opt/homebrew/bin` on this Mac. It skips where `age` or `age-keygen` is not on PATH.
- Mutation spot checks (run in-process against the SQLite param, nothing committed): printing the minted value, logging it, skipping the revoke on failure and revoking the wrong id each make tests fail. A first "leak" mutation passed everything because it hooked `sealed.seal` while the tests inject the sealer; I redid it on the mint call, where it is caught.

## Issues / Blockers
- None blocking. The live path (`_live_org()` logs in to a real Infisical; `_gh_subprocess` runs a real `gh`) was deliberately never executed. Its logic is covered through the injected fakes only; the first real run is the CEO-gated step.
- **Admin-host check and file permissions.** `is_admin_host()` only checks that the `setup` credential file exists, via `os.path.exists`. `/etc/infisical` is root-only on the Mac, so a watchdog running as a non-root user may not be able to stat that path and will read the answer as "not admin": the pass becomes a silent no-op. Check this before relying on the watchdog; the CLI from a root or `sudo` shell does not have the problem.
- A live `provision` creates the `org-node` identity on first use (the fifth of five). That needs the CEO's go, which this task did not have.

## Notes for Reviewer
- **Behaviour change in W4.1 code to confirm:** `export-hosts` now also leaves out `identity_ready` rows (`NOT_EXPORTED = (left, pending_identity, identity_ready)`). A provisioned node has no probe yet, so nothing should route to it. W4.1's tests still pass; say if you would rather export it.
- **Decision, deploy key storage:** its own column `hosts.deploy_pubkey`, not `config_json`. `config_json` is what `export-hosts` writes to `hosts.yaml`, and a deploy key does not belong there.
- **Decision, provision order:** claim row -> mint -> record the secret id at once -> seal -> deploy key -> store + flip. Seal comes before the deploy key so the step most likely to fail (age missing) fails before anything exists on GitHub. Any failure after the mint revokes what was made; if the revoke also fails the error is `provision_orphans`, it names `kind:id`, and the claim row keeps the ids so the next run finishes the cleanup. A claim younger than 10 minutes with no ciphertext answers `busy`.
- **Secret value:** only ever inside the age ciphertext after the seal step. Tests assert the fake secret is absent from stdout, stderr, log records, every column of every hub table, and gh and Infisical request bodies, on success and on failure paths.
- `tailscale_device` and `authorized_keys` stay `_not_wired`: `leave --live` therefore still ends `partial` with exit 1 until G3 and W2.8.
- `sealed --host` stamps `fetched_at` the first time (and logs `node_sealed_fetch`), which the brief did not ask for; it lets the hub see whether the ciphertext was ever handed over.
- **task-3bf2da7c** also edits `runners/watchdog.py`. My change is one new function plus one try/except call right after `_retry_letters`, so a rebase should be trivial.
- **Left for W4.3:** delivering the ciphertext to the node and opening it with the node's age identity (`sealed.open()` exists, nothing calls it). **Left for live wiring:** the CEO's go, `ORG_W42_PROVISION=1` on the Mac, the `/etc/infisical` permission check above, and the two unwired revokers.
- Payload format (what the node will open): JSON `{"v":1,"host","client_id","client_secret"}`.
- Nothing outside the declared touches was edited. The worktree has no `.venv`; tests were run with the main checkout's interpreter.

## Skill learning
- MISSING [no owner] : a local throwaway Postgres for `ORG_TEST_DB_URL` — Postgres 16 is at `/opt/homebrew/opt/postgresql@16/bin` (not on PATH). The scratchpad path is over the 103-byte unix-socket limit, so the first `pg_ctl start` died; working recipe: `initdb -D pgdata -A trust -U orgtest`, then `pg_ctl -D pgdata -o "-p 55432 -c listen_addresses=127.0.0.1 -c unix_socket_directories=" -w start`, then `createdb -h 127.0.0.1 -p 55432 -U orgtest org_test` · evidence: this task, 4 tries · proposal: one line in the ops traps memory index or the `tests/test_w41_hq_join.py` header
- COSTLY [no owner] : GateGuard `Write` fires after a whole ~650-line test file is generated, so the file is sent twice (and once more for the sealed test) · evidence: task-cd15c555 · prevented by: (untested idea, n=1) write a one-line stub to the path first to clear the gate, then write the real content
- MISSING [no owner] : a mutation spot check needs the mutation on the path the tests actually exercise; my first "leak" mutation hooked `sealed.seal` while the tests inject the sealer, so it passed everything and proved nothing · evidence: this task, first mutate.py run · prevented by: make one test fail first to show the mutated call is reached before reading a pass as coverage
