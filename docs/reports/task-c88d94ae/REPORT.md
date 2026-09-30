# task-c88d94ae: Org Mesh W4.5, the join endpoint behind traefik

Branch `agent/developer-task-c88d94ae`. Repo files only; nothing was deployed and no live system was touched.

## What was built

1. `deploy/join/docker-compose.join-proxy.yml`: one `alpine/socat:1.8.0.3` container (project and container name `org-join-proxy`) on the external network `n8n_default`, `extra_hosts: host.docker.internal:host-gateway`, `socat TCP-LISTEN:8080,fork,reuseaddr TCP:host.docker.internal:8791`. `read_only`, `restart: always`, `mem_limit: 32m`, `pids_limit: 128`, `cap_drop: ALL`, `no-new-privileges`, non-root user 65534. No `ports:`, `volumes:`, `environment:`. Exactly six labels: `traefik.enable`, router `org-join` (rule ``Host(`webhook.mooniex.com`) && PathPrefix(`/org-join`)``, `websecure`, `tls`, `certresolver=mytlschallenge`), service port 8080.
2. `tools/join_api.py`: `check_bind(addr)` allowlist (IPv4 only; `127.0.0.0/8` or `172.16.0.0/12`), `--bind` / env `JOIN_API_BIND`, default `BIND_HOST = 127.0.0.1` (empty env = default). `main()` checks it before the database and exits 2 through argparse with a one-line reason; `JoinServer(bind=...)` enforces the same check, so a programmatic caller cannot bind `0.0.0.0` either. The "listening on" log line now prints the real bound address.
3. `deploy/join/org-join.service`: `Environment=JOIN_API_PUBLIC_URL=https://webhook.mooniex.com` and `Environment=JOIN_API_TRUST_FORWARDED=1`; `ExecStart` is now `/bin/sh .../deploy/join/bind-docker0.sh <the old infisical_setup.py run Agents-Core prod --as contabo -- setpriv ... python -m tools.join_api --port 8791>`; `After=`/`Wants=docker.service` added.
4. `deploy/join/bind-docker0.sh` (new, 28 lines): the docker0 resolution.
5. `deploy/join/README.md`: flow diagram, how docker0 is resolved, install (in order), the checks, the firewall/502 troubleshooting note, rollback.
6. `tests/test_w45_bind.py`: 55 tests.

## How docker0 is resolved

A wrapper, not an `ExecStartPre`. `bind-docker0.sh` is the first word of `ExecStart`; it runs `ip -4 -o addr show dev docker0`, takes the first address, exports it as `JOIN_API_BIND` and `exec`s the rest. It runs before the Infisical fetch on purpose: with no docker0 (docker down) it exits 1 before any Infisical API call, so `Restart=on-failure` / `RestartSec=10` does not hit Infisical every 10 s. The variable reaches join_api because `infisical_setup.py run` does `os.execvpe(argv[0], argv, {**os.environ, **secrets})` (tools/infisical_setup.py:708) and `setpriv` keeps the environment. Nothing is written to disk and the unit carries no address. `host-gateway` (docker's default `host-gateway-ip`) is the same docker0 address, so the container and the endpoint agree. A docker0 address outside `172.16.0.0/12` (custom `bip`) makes join_api exit 2 with the reason in the journal; it never widens.

## Deploy (CTO, on Contabo, after merge and pull)

```bash
cd /opt/MoonieXHQ/Agents/Core
ip -4 -o addr show dev docker0                      # inet 172.17.0.1/16
docker network ls --filter name=n8n_default
docker compose -f deploy/join/docker-compose.join-proxy.yml config -q
docker compose -f deploy/join/docker-compose.join-proxy.yml up -d
docker ps --filter name=org-join-proxy --format '{{.Names}} {{.Status}} [{{.Ports}}]'    # Ports empty
docker exec org-join-proxy grep host.docker.internal /etc/hosts                           # = docker0 address
sudo cp deploy/join/org-join.service /etc/systemd/system/ && sudo systemctl daemon-reload
sudo systemctl enable --now org-join
journalctl -u org-join -n 20 --no-pager             # listening on 172.17.0.1:8791
ss -ltnH 'sport = :8791'                            # 172.17.0.1:8791 only
```

Checks: the three curls from the brief (200 + `https://webhook.mooniex.com/org-join` substituted / 403 / 404), plus from a machine that is not Contabo: `curl -m 5 http://194.233.80.26:8791/org-join/join.sh` must be refused or time out.

## Rollback

```bash
docker compose -f deploy/join/docker-compose.join-proxy.yml down
sudo systemctl disable --now org-join
```

## Tests

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest -p no:warnings tests/test_w45_bind.py` | 55 passed |
| `.venv/bin/python -m pytest -p no:warnings` (full suite, once, at the end) | 5262 passed, 190 skipped, 0 failed, 416 s |
| `python scripts/test_maintab.py` | 18 PASS, 0 FAIL, exit 0 |
| `python scripts/test_tab_title.py` | 5 PASS, 0 FAIL, exit 0 |
| `python scripts/test_spawn_tab_routing.py` | 27 PASS, 1 FAIL (`delegate_task reads owner_role from DB and threads it through`), exit 1 |

The one FAIL is not from this change: the same script on an export of the base commit (`git archive HEAD~1`, run from the scratchpad) gives the same 27 PASS and the same single FAIL. This change touches no file that script imports.

Also run by hand: `python -m tools.join_api --bind 0.0.0.0`, `JOIN_API_BIND=:: ...`, `--bind 10.0.0.1` all exit 2 with a clear message; `docker compose -f ... config` (Compose v5.1.0, offline) parses the file and shows the six labels. `shellcheck -s sh bind-docker0.sh` is clean (also a test).

## Not verified, for the CTO

- **Image tag.** `alpine/socat:1.8.0.3` was pinned from memory; there is no network here, so the tag was not pulled. `compose up` fails loudly if it does not exist. After the first pull, replace the tag with the digest (`docker image inspect --format '{{index .RepoDigests 0}}'`).
- **Host firewall.** A container on `n8n_default` reaches the docker0 address through the host's INPUT chain. If Contabo has default-deny INPUT (ufw), check 1 returns 502/504 until that one address and port is allowed from the `n8n_default` bridge. The README says how to tell.
- **Weak host model.** The docker0 address is private and not routed from the internet, but a host on the VPS's own L2 segment could send packets to it. Token checks and the per-IP rate limit still apply. A firewall rule on `INPUT` for non-bridge interfaces would close it if wanted; left out as outside this brief.
- **Rate-limit key.** `JOIN_API_TRUST_FORWARDED=1` keys on the last `X-Forwarded-For` entry. If traefik sees every client as a docker gateway address (userland proxy), all callers share one bucket. Look at one real request's source address in traefik's access log after deploy.
- The container, traefik and systemd are exercised only by the checks above, on Contabo.

## Skill learning

- MISSING [CXO_Protocol_DevSpawn §brief] : the brief says `.venv/bin/python`, but a worker worktree has no `.venv` (it is not tracked); I used `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python` from the main checkout. A brief, or the worker kickoff, should give the interpreter path · evidence: task-c88d94ae
- COSTLY [no owner] : "the three scripts/test_*.py run as scripts" names no files; `pytest.ini` ignores 12 of them. I read it as the three with the `def test_*(tmp) -> bool` harness signature (category (c) in pytest.ini: test_maintab, test_tab_title, test_spawn_tab_routing). It cost one grep pass and a guess · evidence: pytest.ini header, scripts/test_*.py · prevented by: name the three files in the brief
- COSTLY [no owner] : `scripts/test_spawn_tab_routing.py` has 1 standing FAIL on the base commit, so "run as scripts" cannot be read as "must exit 0" without a base comparison (`git archive HEAD~1 | tar -x -C <scratchpad>`, run there) · evidence: same 27 PASS + 1 FAIL at HEAD~1 · prevented by: a known-failing list next to the brief's command
- MISSING [no owner] (global CLAUDE.md "GateGuard fact protocol") : when several Edits on one file are sent in parallel, only the first is blocked and the others are applied, so the blocked one (here the module docstring) lands last and out of order. Send the first Edit alone, then the rest · evidence: tools/join_api.py in this task
