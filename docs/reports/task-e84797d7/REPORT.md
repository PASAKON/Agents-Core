# REPORT task-e84797d7: Org Mesh W4.3, the node side of `hq join`

A new machine runs one command with a join token and ends as a provisioned org node. The hub endpoint (`tools/join_api.py`), the two scripts (`join.sh`, `join.ps1`), the systemd unit and the operator doc are built and tested. The endpoint and `join.sh` are exercised end to end against a real local server in tests. `join.ps1` has never been parsed: this Mac has no `pwsh`. Nothing was run against live Infisical, GitHub, Tailscale, Contabo or winbox; nothing was installed on this Mac; no Postgres server was started.

## Files

| Path | What |
|---|---|
| `tools/join_api.py` | stdlib `ThreadingHTTPServer` on 127.0.0.1 only. `GET /org-join/join.sh`, `join.ps1`; `POST accept`, `POST sealed`. |
| `deploy/join/join.sh` | POSIX sh, Linux + macOS. Nine steps, each idempotent. `--dry-run`. |
| `deploy/join/join.ps1` | Windows PowerShell 5.1, ASCII only. Same nine steps. |
| `deploy/join/org-join.service` | systemd unit for Contabo. **Not installed.** |
| `deploy/join/README.md` | Operator doc: flow, one-liners, exit codes, unit install, W4.5 / G3 needs. |
| `tests/test_w43_join_api.py` | 34 tests x (sqlite, pg). Real server on an ephemeral port. |
| `tests/test_w43_join_scripts.py` | 33 tests: `sh -n`, shellcheck, ASCII, pwsh parse, dry runs, step functions. |

Nothing outside the declared touches was edited. `docs/ops/hq-join.md` is not edited (outside the brief's paths): the CTO may want to fold a pointer to `deploy/join/README.md` into it.

## Endpoint (`tools/join_api.py`)

- Binds `127.0.0.1:<port>` (default 8791). The bind host is a constant, not an option.
- `GET /org-join/join.sh|join.ps1`: `text/plain`, no secret. The hub URL placeholder is replaced with `--public-url` / `JOIN_API_PUBLIC_URL` when set, else with the request's `Host` header (validated; a hostile `Host` leaves no trace in the script).
- `POST accept`: body `{token, host, os, hq_root, pubkey, deploy_pubkey?}` -> `hq_join.accept`. Response `{host, status}`; plus `tailscale_authkey` only when a `TailscaleMinter` is injected. Not wired: G3. A minter that raises or returns junk never fails the join; it is logged by class name only.
- `POST sealed`: `{host, token}`. Needs the token's hash to match the host's `join_tokens` row, `used_at` set, and `used_at` under 24 h old. `202 {"status":"pending"}` until the host is `identity_ready`, then `200 {"status":"ready","ciphertext"}`.
- **One identical `403 {"error":"refused"}`** for every token/host refusal in both routes: wrong token, other host's token, unconsumed, over 24 h, left, revoked, unknown host, malformed shape. Tests compare full responses byte for byte.
- Hardening: 8 KB body cap (exact-cap body is accepted, one byte more is 413), JSON only with a required `Content-Length`, in-memory per-IP limiter (30 / 60 s, all routes share it, bounded memory), no CORS headers, no directory serving, `404` for every other path, `Cache-Control: no-store`, `nosniff`.
- Rate limit key is the socket peer. Behind traefik that is always the proxy, so `--trust-forwarded-for` / `JOIN_API_TRUST_FORWARDED=1` switches to the **last** `X-Forwarded-For` entry (the one the proxy appended; a client-forged earlier entry is ignored). Off by default.
- Logs: `METHOD path status host=<name>`; `-` for an unknown route. Never a body, token, ciphertext or exception text.

## Scripts: the nine steps

1. parse `--token --host --hq-root --hub --dry-run` (`ORG_JOIN_TOKEN` env also accepted, then unset)
2. install git, python3, node 22, age, tailscale, claude (apt / brew / winget / npm); skip what exists
3. keys if absent, 0600: age identity, deploy key, dispatch key
4. POST accept
5. `tailscale up --hostname <host> --advertise-tags=tag:org-node [--authkey <returned>]`, or verify already on the tailnet, else stop with the exact command to run
6. poll `sealed` every 15 s, up to 15 min
7. clone `PASAKON/Agents-Core` to `<hq_root>/Agents/Core` over the deploy key only (`GIT_SSH_COMMAND`, `IdentitiesOnly=yes`)
8. `age -d -i <identity>` | two lines | `infisical_setup.py save <host> --stdin` (root; announced up front), then `node.yaml`
9. probe, print its one-line result

- **Order on the machine is 6, 7, 8, 9** and the ciphertext is held in memory meanwhile. The brief's step 6 (`save`) needs `infisical_setup.py` from the clone, and the clone needs the deploy key, which only works after the Mac has run `provision`. The dry run keeps the brief's nine labels.
- Already joined: `accept` of a used token gives the uniform 403, so the script asks `sealed` instead (200/202 means "already joined with this token"; 403 means "refused"). No disk marker.
- Hub URL must be `https://` (plain `http://` only for `127.0.0.1` / `localhost`), so a typo cannot send the token across a network in clear text. Commit 3c9cdd30.
- Host name is limited to 3-31 characters (see Issues).
- The token is never written to disk, never echoed, never in argv of a long-lived process (the body goes to `curl` on stdin; on Windows to `Invoke-WebRequest` in memory).
- `CLAUDE_CODE_OAUTH_TOKEN` is not fetched. The final message says so.
- Exit codes: `0` node up and probe passed; `2` joined and identity saved but the probe failed; `1` stopped before the node existed.

## node.yaml location chosen

`~/.config/mooniex/node.yaml` (`lib.config.NODE_CONFIG_PATH`, the path `_node_yaml_host` reads), with keys `host`, `os`, `hq_root`. Not `<checkout>/state/node.yaml`: the file the code already looks for exists, so the fallback in the brief was not needed. The dispatch key is at `~/.ssh/org_dispatch` (the path `lib/mesh.py` reads), not under the config dir.

## Tests

| Run | passed | failed | skipped |
|---|---|---|---|
| `tests/test_w43_join_api.py` | 34 | 0 | 34 (the `pg` param: no `ORG_TEST_DB_URL`; the CTO runs it on Contabo) |
| `tests/test_w43_join_scripts.py` | 32 | 0 | 1 (`pwsh` parse: not on PATH) |
| full suite, `.venv/bin/python -m pytest -p no:warnings -p no:cacheprovider` | 5170 | 0 | 190 |
| `python scripts/test_org_tools_registry.py` | ALL PASS | 0 | |
| `python scripts/test_mcp_role_config.py` | 7 | 0 | |
| `python scripts/test_tool_parity.py` | ALL PASS | 0 | |

`scripts/test_org_tools_registry.py` run **under pytest on its own** fails 12 + 1 error with `tests must not touch a real checkout's tasks.db (ADR 0021)`. It is written to run as a script (its header says so) and it only points `db.DB_PATH` at a temp file in `main()`. Same finding as task-3bf2da7c. Run as a script: ALL PASS. Inside the full suite it passes (row above).

The full suite (402 s) started one commit before the last one (3c9cdd30, https-only hub check in `join.sh` / `join.ps1`, +2 bad-argument cases). After that commit `tests/test_w43_join_scripts.py` was re-run alone: 32 passed, 1 skipped, and `shellcheck -s sh deploy/join/join.sh` is clean. `tools/join_api.py` and its tests did not change in that commit.

What the tests cover that matters for review:
- a real server, real sqlite hub DB, real `hq_join.mint/accept/provision` behind it; `provision` is driven with the existing test fakes, no network;
- the identical-403 matrix, the exact 24 h boundary, the body cap boundary, the 404 matrix, rate limit and `X-Forwarded-For` spoofing;
- the token and the ciphertext absent from captured logs, including a hostile `host` value and a 500;
- `join.sh` through the real `curl | sh` pipe shape, with recorder `sudo` / `apt-get` / `brew` / `npm` on PATH and HOME in `tmp_path`: nothing installed, nothing written, nine steps printed;
- every step function called alone (`ORG_JOIN_LIB=1`) against the test server, including real `age` for step 8: the stub `save` receives exactly `client_id\nclient_secret\n`; a wrong key stores nothing; a `node.yaml` naming another host is refused;
- 12 bad-argument cases, including non-https hubs.

## What W4.5 and G3 still have to provide

**W4.5 (traefik):**
- route `https://<public hub name>/org-join/*` -> `127.0.0.1:8791` (the unit binds loopback only);
- two lines in the unit: `Environment=JOIN_API_PUBLIC_URL=https://<public hub name>` and `Environment=JOIN_API_TRUST_FORWARDED=1`. Without the first, `join.sh` learns its hub from the `Host` header; without the second, every caller shares one rate-limit bucket (the proxy);
- TLS terminates at traefik. The scripts refuse a non-https hub, so there is no plain-http fallback to add.

**G3 (CEO gate):**
- a Tailscale OAuth client, wired as the `TailscaleMinter` in `join_api.main()` (one-use, pre-approved, `tag:org-node` pre-auth key), and the `tag:org-node` ACL. Until then `/accept` returns no key and step 5 needs the machine already on the tailnet;
- `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`) stored in Infisical under `Agents-Core` `prod`, so a node reads it with `infisical_setup.py run`.

**Live steps nobody has done:** install and start `org-join.service` on Contabo (after W4.6 review). The unit file, read as written, is unverified under systemd.

## Issues / Blockers

- **`join.ps1` was never parsed.** No `pwsh` here. It is checked only for ASCII and by reading. The PowerShell 5.1 traps I know (native stderr under `Stop`, pipeline re-encoding and CRLF, empty-argument drop, TLS 1.2) are handled in the code, but a parse and a run on Windows are needed before it is trusted. Suggest winbox, or `pwsh` in the W4.7 drill.
- **Install paths are untested beyond syntax, shellcheck and dry run** (apt, brew, nodejs.org tarball with sha256, winget ids). W4.7's container drill is the real test.
- **A joined node's probe will probably fail.** `lib.config.self_host()` (via `_node_yaml_host` and `ORG_HOST`) requires the host to be listed in `config/hosts.yaml`; a freshly joined node is not. That file and `lib/config.py` are outside my touches. The scripts treat the probe as non-fatal (exit 2, message "joined and its identity is saved, but the probe did not pass"). Fix belongs to whichever task exports the hub `hosts` table to a node (`hq_join export-hosts` exists).
- **Host-name length mismatch:** `hq_join.HOST_RE` allows 3-32 characters, `infisical_setup.NAME_RE` allows 2-31. A 32-character name would mint and accept, then fail at `save`. The scripts reject over 31. One of the two regexes should change; both are outside my touches.
- **The probe runs under root** (it needs `infisical_setup.py run` to read the root-only credential), so root-owned files (audit log) can appear in the clone. `PYTHONDONTWRITEBYTECODE=1` stops `.pyc` files only. Worth a look in W4.6.
- **The Tailscale pre-auth key is briefly in the argv of `tailscale up`** (the CLI has no stdin form). One-use and short-lived, but visible to other local users for that moment.
- **The clone trusts github.com on first contact** (`StrictHostKeyChecking=accept-new`, a private `known_hosts` file). A man in the middle on the very first clone could present its own host key. Pinning GitHub's published host keys in the scripts would close it; I did not add them because they are a fact to verify against GitHub, which this task may not contact.
- **A lost Tailscale key cannot be re-issued** on a re-run: `accept` is refused for a used token and the key was in that response. The script then says to run `tailscale up` by hand.
- Nothing is wrong at my tier: no part of this needed more than Sonnet reasoning, but the brief is security-sensitive and I suggest the W4.6 reviewer read `join_api.py` routes and `do_identity` in `join.sh` line by line.

## Skill learning

- MISSING [hq-join brief / W4.3 plan §"what join.sh does"] : the step order is wrong as written. Step 6 runs `infisical_setup.py save` from the checkout, but the checkout (step 7) needs the deploy key, which only works after provisioning (step 6's wait). Correct order: wait, clone, save, probe · evidence: task-e84797d7, `deploy/join/join.sh` `main()`
- MISSING [hq-join / `docs/ops/hq-join.md` §host names] : `hq_join.HOST_RE` (3-32) and `infisical_setup.NAME_RE` (2-31) disagree; a 32-character host joins and then cannot save · evidence: `tools/hq_join.py`, `tools/infisical_setup.py`, task-e84797d7
- MISSING [hq-join / node probe §self_host] : `config.self_host()` needs the node's name in `config/hosts.yaml`; a freshly joined node is not there, so the last join step fails · evidence: `lib/config.py` `_node_yaml_host` / `_env_host`, task-e84797d7
- MISSING [no owner: test hygiene] : `scripts/test_org_tools_registry.py` fails 12 + 1 error under bare `pytest scripts/test_org_tools_registry.py` (ADR 0021 guard) and passes as a script; the task brief lists it as a pytest target · evidence: same finding as task-3bf2da7c; the brief should say `python scripts/test_org_tools_registry.py`
- COSTLY [no owner] : GateGuard `fact-force` blocks the first Write of every new file, 7 files here, one round trip each · evidence: this session · prevented by: batch new-file facts once per file in the same message as the Write call (already known; it cannot be pre-empted)
