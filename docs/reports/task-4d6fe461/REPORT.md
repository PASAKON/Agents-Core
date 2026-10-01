# task-4d6fe461: Org Mesh, CEO gate G3 part 2 (Tailscale pre-auth key + device removal)

## Summary

The join door hands an approved node a one-use, pre-authorized, `tag:org-node` pre-auth key, and `hq_join leave --live` removes that node's tagged device. After CTO review (iteration 2, F1) the key is no longer minted at `/accept`: `/sealed` adds it to the `ready` answer, so it is released only after the CEO has approved the fingerprint. Nothing live was contacted (all Tailscale calls in tests hit a fake server on an ephemeral port); with the two variables unset, behaviour is as before.

## Iteration 2: what changed for CTO-FEEDBACK

- **F1 (blocking), the key before approval.**
  - `tools/join_api.py`: `_route_accept` no longer calls the minter and the answer is `{host, status}` only. `_route_sealed` calls the new `_mint_authkey(h, host)` only after every gate has passed (token valid, within 24 h, host not `left`, host not `pending`, `sealed_ciphertext` returned a live ciphertext), outside the database slot, and adds `tailscale_authkey` to the `ready` JSON. Pending (202) and every 403 never reach it. A minter failure returns `ready` + ciphertext with no key field and one warning.
  - `deploy/join/join.sh` and `deploy/join/join.ps1`: steps 5 and 6 swapped. Step 5 is now the wait and reads `tailscale_authkey` from the sealed answer; step 6 is the tailnet. `main`/`Join-OrgNode` run `do_install; do_wait_sealed; do_tailscale; do_clone`. The "already on the tailnet" path and the "join by hand" message are unchanged. `sh join.sh --dry-run` prints `[1/9]` to `[9/9]` in the order they run (5 wait, 6 tailnet); a test pins it.
  - **Nothing between accept and sealed needs the tailnet** (checked by reading `join.sh`; `join.ps1` is the same shape): step 4 installs from public repositories (apt incl. `pkgs.tailscale.com`, brew, npm; no tailnet address anywhere in the file, grep for `100.x` and `ts.net` finds none); step 5 posts to `$HUB`, the hub's public URL (`@@ORG_JOIN_HUB@@` or `--hub`); step 7's clone is `git@github.com` and pip is PyPI. Everything that does come after (clone, `infisical_setup.py save`, probe) is also after step 6, so it has the tailnet where it did before.
  - Docs: `deploy/join/README.md` (flow diagram, "Tailscale pre-auth key") and `docs/ops/hq-join.md` say the key is released only after approval and why.
- **Note 3**: the minter warning is now `tailscale minter failed for <host>: TailscaleError (HTTP <status>)`: class name and the integer status only, never a body or message (tested with a message that contains a key-shaped string).
- **Note 7**: the "ONE value" comment in `deploy/join/org-join.service` now names the two Tailscale values.

## Files changed (whole task)

- `lib/tailscale_api.py` (new, stdlib `urllib` only). `TailscaleClient`: access token cached until 60 s before expiry (thread-safe, one retry on a 401); `mint_authkey(host)` posts exactly the body the brief gave (`reusable:false, ephemeral:false, preauthorized:true, tags:["tag:org-node"]`, `expirySeconds:3600`, description `org-node:<host>`), host checked with `lib.config.HOST_NAME_RE` first; `delete_device(host)` lists devices, deletes only the one whose hostname is the host AND whose tags include `tag:org-node`, refuses two matches, treats none or a 404 as done and returns `False`. Base URL, HTTP opener, clock and timeout are injectable. `from_env(environ)` returns `None` for neither variable, a client for both, and a `ValueError` naming both variables for one without the other.
- `tools/join_api.py`: `main()` passes `minter=client.mint_authkey` when `from_env` returns a client (half config = `p.error`, exit 2, before the DB is touched); the mint now lives in the `/sealed` route (above).
- `tools/hq_join.py`: `tailscale_revoker(client=None)`; `wired_revokers(..., tailscale=None)` fills the `tailscale_device` slot when a client is given or the environment holds one. `default_revokers()` unchanged, so the leg is live only with `ORG_W42_PROVISION=1`. Flag without the variables: `not wired yet`; half the variables: refused, both named.
- `deploy/join/join.sh`, `deploy/join/join.ps1`, `deploy/join/org-join.service`, `deploy/join/README.md`, `docs/ops/hq-join.md`: as above.
- `tests/test_w47_tailscale.py` (new, 70 tests), `tests/test_w43_join_api.py`, `tests/test_w43_join_scripts.py`, `tests/test_w46b_node_fixes.py` (updated for the new order and answer).
- `docs/reports/task-4d6fe461/REPORT.md`: this file.

## For the CEO: exactly what to enter

| Where | What |
|---|---|
| Tailscale ACL, `tagOwners` | `"tag:org-node": ["autogroup:admin"]` (any owner you prefer) |
| Tailscale OAuth client scopes | **Auth Keys: Write** and **Devices Core: Write**, nothing else |
| Tags the client may use | `tag:org-node` only |
| Infisical project / env / folder | **Agents-Core** / **prod** / **/org-join** (the folder the `org-join` unit already injects) |
| Secret 1 | `TAILSCALE_OAUTH_CLIENT_ID` = the OAuth client ID |
| Secret 2 | `TAILSCALE_OAUTH_CLIENT_SECRET` = the OAuth client secret |

Both names pass `infisical_setup.lint_name` (PLAN §4b). No unit change. They take effect the next time the door opens. To check, `journalctl -u org-join -n 40 --no-pager | grep -E 'infisical run|listening on'` must show `(minter wired)`; `(minter not wired)` means neither name arrived, and one without the other makes the endpoint refuse to start. The first real proof is the first join after the CEO approves it: the `ready` answer carries the key and step 6 prints `joined the tailnet`. For `leave --live` the same two names plus `ORG_W42_PROVISION=1` must be in the environment of the process on the Mac that runs it.

## Commits

On branch `agent/developer-task-4d6fe461`:

- 4480d4fc join: lib/tailscale_api client, wired into join_api minter and hq_join leave
- 5e6b8a16 join: tests for the Tailscale client and docs for the OAuth client setup
- 383b310b join: join_api docstring names the Tailscale values; task report
- d7e2ff99 join: release the tailnet key with the sealed answer, after approval, not at accept
- one final commit: this report (sha in the submitted report)

## Tests

- Full suite, once, interpreter `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python` (the worktree has no `.venv`): `python -m pytest -p no:warnings`: **5943 passed, 0 failed, 361 skipped** in 480.95 s (the skips are Postgres params with `ORG_TEST_DB_URL` unset, and `pwsh`-only parse tests). Launched through a one-line wrapper that resets SIGINT to default, see "Issues" for why.
- Join-related files together (`test_w47`, `w41`, `w42_provision`, `w43_join_api`, `w43_join_scripts`, `w44b`, `w44c`, `w45_bind`, `w46a`, `w46b`, `w46c_*`): 839 passed, 333 skipped, 0 failed.
- `tests/test_w47_tailscale.py` alone: 70 passed. `test_w43_join_api` + `test_w43_join_scripts` + `test_w46b_node_fixes`: 124 passed, 41 skipped.
- New tests for F1: accept never returns a key and never calls the minter, even with one wired (also on a refused accept); sealed pending never calls it; every sealed 403 never calls it, including approved hosts with a wrong token, another host's token, a token past 24 h, a host that left and a revoked secret; sealed `ready` returns the key and calls the minter once per ready answer; no minter means no key field; a failing or junk minter still returns `ready` + ciphertext; the warning is class + integer status only; the key is in no log line. Script side: accept step leaves `TS_KEY` empty; wait step takes the key from the sealed answer and never prints it; a pending node mints nothing; the tailnet step runs `tailscale up --auth-key ... --advertise-tags=tag:org-node` with that key and forgets it; the already-on-the-tailnet path and the join-by-hand message are kept; static checks that accept never reads `tailscale_authkey`, `main` order, `Step 5`/`Step 6` labels in both scripts, and the dry-run order.
- `python scripts/test_org_tools_registry.py`: ALL PASS. `python scripts/test_mcp_role_config.py`: OK, 0 failures. `python scripts/test_tool_parity.py`: ALL PASS.

## Issues / Blockers

- None blocking. Nothing was verified against the real Tailscale API; request and answer shapes are from the Tailscale API as I remember it. A mismatch fails safe, and the first real join is the first real proof. The "pick `tag:org-node` and no other" tag restriction in the OAuth client is from memory of the console, not tested.
- **`join.ps1` was edited but not run or parsed with PowerShell** (`pwsh` is not installed here, so `test_join_ps1_parses_under_powershell` is skipped). The edits mirror `join.sh` one for one, and the ASCII-only test and the new static order/label tests pass. A Windows node (winbox) should do the first real join with `--dry-run` first.
- **Correction to my first report.** I wrote that `tests/test_w46b_node_fixes.py::test_echo_is_restored_on_interrupt_too` failed once because of load. That was wrong. It fails every time pytest is started as a shell background job (`cmd &`): a non-interactive shell starts `&` jobs with SIGINT ignored, the setting is inherited through exec, and the test's `kill -INT` on the inner `sh` then does nothing. Evidence: the single test passes in the foreground (0.43 s) and fails as `( ... ) &` alone (20 s, no other load); the same background launch through a wrapper that sets SIGINT back to default passes (0.39 s); the full suite through the wrapper is 5943 passed, 0 failed. It is not a product bug and not related to this change.

## Notes for Reviewer

1. **Behaviour change in `join.sh` without a minter.** Today (no OAuth client in Infisical yet) a node that is not already on the tailnet used to stop at step 5, before the wait. Now it waits for approval, receives the identity in memory, and then stops at step 6 with the "join by hand" message; running the same command again continues (accept 403, then `/sealed` says "already joined", then step 5 fetches the ciphertext again). Nothing is lost, but the operator approves a node that may then need a manual `tailscale up`.
2. **Each `ready` answer mints a key.** The "already joined" probe inside `do_accept` (a re-run with a used token) also calls `/sealed` and gets a ready answer, so a re-run of an approved node mints one key that is thrown away; it expires within the hour and is one-use. Avoiding that would need a probe flag on `/sealed`, which changes the contract; not done. The poll loop stops at the first 200, so a normal join mints exactly one.
3. The mint happens inside the `/sealed` request, so a slow Tailscale (client timeout 10 s) delays that one answer; it is outside the database slot, under the endpoint's 15 s request timeout, and a failure still returns the identity.
4. **The token form also sends `grant_type=client_credentials`**, which the brief did not list; it is the standard OAuth parameter. One line to drop in `access_token()` if Tailscale rejects it.
5. **The public endpoint holds the OAuth client secret in memory** (before: only the `org_join` DSN). The blast radius is the scopes and the one tag the CEO ticks. A `security_engineer` look at "mint in the public process" is worth a line in W4.6. With F1 a leaked token alone no longer yields a key, and the secret is only used after the approval gate.
6. `leave` removes the device, not the pre-auth key (an unused key expires in 1 h). Hostname match is case-insensitive; the tag test is exact. No environment variable sets the base URL, redirects are not followed, errors carry status + Tailscale's `message` only with key-shaped strings and held secrets replaced by `[redacted]`.
7. `docs/ops/hq-join.md` lines about provisioning "step 4 / step 6" (around 321 and 330) are provisioning steps, not join steps, and are unchanged; line ~507 ("at step 6") is an old W4.3 sentence I left alone.
8. `join.sh` passes the key as an argument to `tailscale up --auth-key` (its own comment at the call says so); newer `tailscale` accepts `--auth-key=file:<path>`. Not changed.

## Skill learning

- WRONG [my own earlier report in this task, "Skill learning" COSTLY on the pty test] : I called `test_echo_is_restored_on_interrupt_too` "load-sensitive". It is not: it fails whenever pytest runs as a `&` shell job because SIGINT is inherited as ignored. · evidence: task-4d6fe461, single-test runs foreground pass / `( ... ) &` fail / wrapper pass, and full suite 5943 passed after the fix · fix: launch long test runs in the foreground or with `python -c 'import signal,os,sys; signal.signal(signal.SIGINT, signal.SIG_DFL); os.execvp(sys.argv[1], sys.argv[1:])' <cmd>`
- MISSING [CXO_Protocol_DevSpawn §brief template] : the brief's full-suite command must say how to run it: a `&` job (and apparently a plain background call that goes through `&`) makes the pty tests in `tests/test_w46b_node_fixes.py` fail with a missing `inner.rc`; foreground or a SIGINT-reset wrapper passes. · evidence: task-4d6fe461, two false-failure full runs (about 9 minutes each)
- MISSING [CXO_Protocol_DevSpawn §brief template] : the worktree has no `.venv`, so `.venv/bin/python -m pytest` does not run; the interpreter is `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python`. · evidence: task-4d6fe461
- MISSING [CXO_Protocol_DevSpawn §brief template] : `scripts/test_org_tools_registry.py` is a script, not a pytest file (under `pytest` it fails 12 + 1 error on the ADR 0021 guard; as `python scripts/...` it passes); the brief should say so. · evidence: task-4d6fe461
- COSTLY [no owner] : I decided a flaky-looking failure was "load" after 3 passing re-runs and wrote it into the report; the second occurrence, with nothing else running, is what forced the real cause. Two foreground passes say nothing when the failing run had a different launch method. · evidence: task-4d6fe461 · prevented by: when a test passes alone and fails in the full run, diff the launch (background, env, tty) before blaming load
- COSTLY [no owner] : GateGuard in a parallel batch of Edits to one file rejects the first call but applies the others, so edits can land out of order; the rejected one needs a second round. · evidence: task-4d6fe461 · prevented by: first edit of each file alone, then batch
- COSTLY [no owner] : doc-pin and order-pin tests (`tests/test_w46c_node_project.py:193`, `tests/test_w46b_node_fixes.py` order lists, `test_a_recording_python_sees_dash_I_...` expecting 3 python calls in accept+clone) break on a step swap or a removed json_get; grep `tests/` for the function and doc names before moving a step. · evidence: task-4d6fe461 · prevented by: that grep
