# task-4d6fe461: Org Mesh, CEO gate G3 part 2 (Tailscale pre-auth key + device removal)

## Summary

When the Tailscale OAuth client is in the join endpoint's environment, `/accept` now hands each node a one-use, pre-authorized, `tag:org-node` pre-auth key, and `hq_join leave --live` removes that node's tagged device from the tailnet. Nothing live was contacted: every Tailscale call in the tests goes to a fake HTTP server on an ephemeral port, and with the two variables unset all behaviour is exactly as before.

## Files changed

- `lib/tailscale_api.py` (new, stdlib `urllib` only). `TailscaleClient`: access token cached until 60 s before expiry (thread-safe, one retry on a 401); `mint_authkey(host)` posts exactly the body the brief gave (`reusable:false, ephemeral:false, preauthorized:true, tags:["tag:org-node"]`, `expirySeconds:3600`, description `org-node:<host>`), host checked with `lib.config.HOST_NAME_RE` first; `delete_device(host)` lists devices, deletes only the one whose hostname is the host AND whose tags include `tag:org-node`, refuses two matches, treats none or a 404 as done and returns `False`. Base URL, HTTP opener, clock and timeout are injectable. `from_env(environ)` returns `None` for neither variable, a client for both, and a `ValueError` naming both variables for one without the other.
- `tools/join_api.py`: `main()` passes `minter=client.mint_authkey` when `from_env` returns a client; half a configuration is `p.error` (exit 2) before the database is touched. Docstring and the `TailscaleMinter` comment updated. The accept route is untouched: a minter exception still means accept succeeds, no key field, one warning with the class name only.
- `tools/hq_join.py`: new `tailscale_revoker(client=None)`; `wired_revokers(..., tailscale=None)` puts it in the `tailscale_device` slot when a client is given or the environment holds one. `default_revokers()` is unchanged, so the leg is live only with `ORG_W42_PROVISION=1`. Without the variables it stays `not wired yet` (message now names the flag and the two variables); with half of them it refuses and names both.
- `deploy/join/README.md`, `docs/ops/hq-join.md`: the two Infisical names, the OAuth scopes, `tag:org-node` and the `tagOwners` line, how to check the minter is wired (journal), what the endpoint can do if compromised, and the `leave` behaviour.
- `tests/test_w47_tailscale.py` (new): 67 tests against `FakeTailscale`.
- `docs/reports/task-4d6fe461/REPORT.md`: this file.

`deploy/join/join.sh` step 5 was read, not changed: line 511 takes `tailscale_authkey` from the accept answer, lines 550 to 552 run `tailscale up --auth-key "$TS_KEY" --hostname "$HOST" --advertise-tags=tag:org-node`, and with no key it still dies with the "join by hand" instructions (line 555).

## For the CEO: exactly what to enter

| Where | What |
|---|---|
| Tailscale ACL, `tagOwners` | `"tag:org-node": ["autogroup:admin"]` (any owner you prefer) |
| Tailscale OAuth client scopes | **Auth Keys: Write** and **Devices Core: Write**, nothing else |
| Tags the client may use | `tag:org-node` only |
| Infisical project / env / folder | **Agents-Core** / **prod** / **/org-join** (the folder the `org-join` unit already injects) |
| Secret 1 | `TAILSCALE_OAUTH_CLIENT_ID` = the OAuth client ID |
| Secret 2 | `TAILSCALE_OAUTH_CLIENT_SECRET` = the OAuth client secret |

Both names pass `infisical_setup.lint_name` (PLAN §4b). No unit change: the unit already runs `infisical_setup.py run Agents-Core prod --as contabo --path /org-join`. They take effect the next time the door opens. To check, `journalctl -u org-join -n 40 --no-pager | grep -E 'infisical run|listening on'` must show `(minter wired)`; `(minter not wired)` means neither name arrived, and one without the other makes the endpoint refuse to start. For `leave --live` the same two names plus `ORG_W42_PROVISION=1` must be in the environment of the process on the Mac that runs it.

## Commits

See `git log` on the branch `agent/developer-task-4d6fe461`:

- 4480d4fc join: lib/tailscale_api client, wired into join_api minter and hq_join leave
- 5e6b8a16 join: tests for the Tailscale client and docs for the OAuth client setup
- one final commit: the last `join_api.py` docstring line and this report (sha in the submitted report)

## Tests

- `tests/test_w47_tailscale.py`: 67 passed, 0 failed, 0 skipped.
- Join-related files together (`test_w47`, `w41`, `w42_provision`, `w43_join_api`, `w43_join_scripts`, `w45_bind`, `w46a`, `w46b`, `w46c_*`): 724 passed, 323 skipped (the skips are the Postgres params, `ORG_TEST_DB_URL` unset), 0 failed.
- Full suite, once at the end, with the main checkout's interpreter (the worktree has no `.venv`): `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings`: **5929 passed, 1 failed, 356 skipped** in 553.94 s. The one failure is `tests/test_w46b_node_fixes.py::test_echo_is_restored_on_interrupt_too`, a pty timing test of `join.sh` (it timed out waiting for `inner.rc`; last prompt seen `Join token (typing is hidden): `). It passed 3 of 3 re-runs alone and in the 724-test run above. I ran the three scripts below while the suite was still running, so I read it as load, not as a regression; I did not run the suite on the base commit.
- `python scripts/test_org_tools_registry.py`: ALL PASS. `python scripts/test_mcp_role_config.py`: OK, 0 failures. `python scripts/test_tool_parity.py`: ALL PASS. Note: run under `pytest`, `scripts/test_org_tools_registry.py` fails 12 and errors 1 with `tests must not touch a real checkout's tasks.db (ADR 0021)`; its header says to run it as a script, and as a script it passes.

## Issues / Blockers

- None blocking. Nothing was verified against the real Tailscale API. The request and answer shapes (`/api/v2/oauth/token`, `/tailnet/-/keys`, `/tailnet/-/devices`, `/device/{id}`; fields `access_token`, `expires_in`, `key`, `devices[].id/hostname/tags`) are from the Tailscale API as I remember it. A mismatch fails safe (accept still succeeds with no key; a leave step reports failed), but the first real join is the first real proof.
- The tag-restriction behaviour of the OAuth client ("pick `tag:org-node` and no other") is from memory of the Tailscale console, not tested.

## Notes for Reviewer

1. **The token form also sends `grant_type=client_credentials`.** The brief said "form body client_id + client_secret"; the third field is the standard OAuth client-credentials parameter. If Tailscale rejects it, drop it in `access_token()`; one line.
2. **The public endpoint now holds the OAuth client secret in memory** (before: only the `org_join` DSN). This is the shape the brief asked for. The blast radius is whatever the CEO ticks, hence the exact scopes and the single tag in the docs. A `security_engineer` look at "mint in the public process" vs a non-public minter is worth one line in W4.6.
3. **The accept warning logs the class name only** (`TailscaleError`), as the brief said, so the journal does not show the HTTP status or Tailscale's reason. The status is a safe integer; adding it to that one log line in `_route_accept` would make a wrong scope diagnosable. I did not change it.
4. **`leave` removes the device, not the pre-auth key.** An unused key (the node left before step 5) expires within the hour by itself. Deleting it would need a list-keys call and was not asked for.
5. **Hostname match is case-insensitive** (hosts are lowercase by regex), so a differently-cased device cannot make an absent device look present or the reverse. The tag test is exact.
6. **No env variable for the base URL on purpose**; the redirect handler refuses to follow redirects so the bearer token cannot leave the host; an error message carries status + Tailscale's `message` only, with control characters removed and key-shaped strings and held secrets replaced by `[redacted]`. Each of these has a test.
7. `deploy/join/org-join.service` line 20 still says the endpoint gets "ONE value". It is a comment in a file outside my touches, so I left it; worth one line when someone next touches that unit.
8. `join.sh` passes the key as an argument to `tailscale up --auth-key` (it says so in a comment at line 550; the key is single use and lives at most an hour). Newer `tailscale` accepts `--auth-key=file:<path>`; not changed, outside touches.
9. The Postgres-param tests in the join suites are skipped without `ORG_TEST_DB_URL`; none of my 67 tests need it.

## Skill learning

- MISSING [CXO_Protocol_DevSpawn §brief template] : the worktree has no `.venv`, so the brief's `.venv/bin/python -m pytest` does not run; the interpreter is `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python`. · evidence: task-4d6fe461, no `.venv/bin/python` in the worktree
- MISSING [CXO_Protocol_DevSpawn §brief template] : `scripts/test_org_tools_registry.py` is a script, not a pytest file: under `pytest` it fails 12 + 1 error on the ADR 0021 guard, as `python scripts/test_org_tools_registry.py` it passes. The brief should say "run as python scripts/...". · evidence: task-4d6fe461, runs above
- COSTLY [no owner] : GateGuard in a parallel batch of Edits to one file rejects the first call but applies the others, so edits can land out of order and the rejected one needs a second round per file. Do the first edit of each file alone, answer the gate, then batch the rest. · evidence: task-4d6fe461, `docs/ops/hq-join.md` and `deploy/join/README.md` edits · prevented by: one single-edit call per new file before any batch
- COSTLY [no owner] : a doc-pin test (`tests/test_w46c_node_project.py::test_no_doc_tells_a_node_to_run_under_agents_core_prod`) forbids lines matching `run Agents-Core prod --as <?(host|node)` in `docs/ops/hq-join.md`; writing a Tailscale/leave example there without reading that test first would have broken it. · evidence: task-4d6fe461, `tests/test_w46c_node_project.py:193` · prevented by: grep `tests/` for the doc's file name before editing a doc
- COSTLY [no owner] : `tests/test_w46b_node_fixes.py::test_echo_is_restored_on_interrupt_too` (a pty test) failed once in a 9-minute full run and passed 3 of 3 alone: it is load-sensitive. n=1, so a note, not a rule. · evidence: task-4d6fe461, full-suite run 2026-10-01 · prevented by: do not run other work while the full suite runs
