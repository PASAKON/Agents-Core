# deploy/join: the node side of `hq join` (Org Mesh W4.3)

One command on a new machine, one tap on the hub side, no login and no secret typed.

```
curl -fsSL https://<hub>/org-join/join.sh | sh -s -- --token <t> --host <name> [--hq-root <path>]     # Linux, macOS
iwr -UseBasicParsing https://<hub>/org-join/join.ps1 | iex                                            # Windows (elevated)
```

The Windows form cannot take arguments through `iex`, so it reads `$env:ORG_JOIN_TOKEN` and
`$env:ORG_JOIN_HOST` (and `ORG_JOIN_HQ_ROOT`). The same arguments as `join.sh` work too:
`& ([scriptblock]::Create((iwr -UseBasicParsing https://<hub>/org-join/join.ps1).Content)) --token <t> --host <name>`.
Keeping the token out of the command line: `curl ... | ORG_JOIN_TOKEN=<t> sh -s -- --host <name>`.

| File | What it is |
|---|---|
| `join.sh` | POSIX sh, Linux + macOS. `--dry-run` prints the nine steps and changes nothing. |
| `join.ps1` | Windows PowerShell 5.1, ASCII only. Same steps, same messages. |
| `org-join.service` | systemd unit for the hub endpoint (`tools/join_api.py`) on Contabo (W4.5). |
| `bind-docker0.sh` | Start-up wrapper of that unit: exports `JOIN_API_BIND` = the docker0 IPv4 address. |
| `docker-compose.join-proxy.yml` | The socat container and traefik labels that put `/org-join` on the internet (W4.5). |
| `tools/join_api.py` | The endpoint the two scripts talk to. |

## The flow

```
operator (phone)           hub (Contabo)                     new machine                      Mac (provisioner)
  Run Inbox: mint --host X ->  join_tokens row
  token, 15 min            <-
                                                   curl .../join.sh | sh --token T --host X
                                                   2 install  3 keys (age, deploy, dispatch)
                              POST /accept  <---   4 accept: token + age pubkey + deploy pubkey
                              hosts: pending_identity
                              {host, status, tailscale_authkey?} --->  5 tailscale up
                                                   6 poll POST /sealed every 15 s ...
                                                                                              hq_join provision X
                              node_secrets.ciphertext <---------------------------------------  (mint Infisical secret,
                              hosts: identity_ready                                              seal to X's age key,
                                                                                                 register deploy key)
                              200 {ciphertext} --->   7 clone Agents-Core (deploy key)
                                                   8 age -d | infisical_setup.py save X --stdin ; node.yaml
                                                   9 probe
```

Steps 6 and 7 are in the order the machine needs them, not the order the nine are listed in the
task: the deploy key only works once the Mac has provisioned the node, and `save` is a script
from the clone.

Every step is safe to repeat. After any failure, run the same command again: a token that already
joined this host is recognised through `/sealed`, and keys, clone, venv and node.yaml are kept.

## What each side sees

- The token goes in a request body under TLS. It is never a URL, a header, a file, or a line of
  output. `join.sh` takes it from `--token` or `ORG_JOIN_TOKEN` (and unsets the variable at once).
- The node's client id and secret exist on the node only as age ciphertext until step 8, where
  `age -d | python | infisical_setup.py save` moves them over pipes. `save` (root, `/etc/infisical`,
  0600) is the only thing that stores them. On Windows one python process does the same chain,
  because a PowerShell pipeline re-encodes and adds CRLF.
- The endpoint answers every token problem with the same `403 {"error":"refused"}`. A wrong
  token, another host's token, an expired one, a used one and "not provisioned" cannot be told
  apart from outside. `/sealed` also stops answering 24 hours after the token was used.
- `CLAUDE_CODE_OAUTH_TOKEN` is not fetched. The node reads it at run time with
  `infisical_setup.py run Agents-Core prod --as <host> -- <command>`.

## Exit codes (`join.sh`)

`0` the node is up and the probe passed. `2` joined and identity saved, but the probe failed (the
line above says why). `1` stopped before the node existed; the message says what to change.

## Putting the endpoint on the internet (W4.5)

```
internet -> traefik (n8n-traefik-1, :443, /org-join) -> org-join-proxy (socat :8080, n8n_default)
         -> host.docker.internal:8791 = the docker0 address -> tools/join_api.py
```

traefik only has the docker provider, and a host process on `127.0.0.1` is out of its reach.
So `join_api` listens on the docker0 address (`172.17.0.1` by default) and a socat container
forwards to it. Nothing is published on the host: the compose file has no `ports:`, and
`194.233.80.26:8791` answers nothing.

**How docker0 is resolved.** `deploy/join/bind-docker0.sh` is the first word of the unit's
`ExecStart`. It runs `ip -4 -o addr show dev docker0`, exports the address as `JOIN_API_BIND` and
execs the rest (Infisical fetch, `setpriv`, `python -m tools.join_api`; all keep the
environment). It is a wrapper and not an `ExecStartPre`, so a box with no docker0 fails before
the Infisical call instead of every `RestartSec`, and no address is written to disk. The address
is checked twice: `tools/join_api.py` accepts `--bind` (env `JOIN_API_BIND`) only inside
`127.0.0.0/8` or `172.16.0.0/12`, and exits 2 on `0.0.0.0`, `::`, a hostname, a public address or
a LAN address. No docker0 address, or one outside that range, stops the service; it never
falls back to a wider bind.

The unit also sets `JOIN_API_PUBLIC_URL=https://webhook.mooniex.com` (what `join.sh` is told it
came from; without it the hub address would come from the request's `Host` header) and
`JOIN_API_TRUST_FORWARDED=1` (rate-limit on the caller's address that traefik appends to
`X-Forwarded-For`, not on the proxy container).

### Install (the CTO, on Contabo, after this is merged and pulled)

```bash
cd /opt/MoonieXHQ/Agents/Core
# 0. look first, nothing changes
ip -4 -o addr show dev docker0                  # inet 172.17.0.1/16, inside 172.16.0.0/12
docker network ls --filter name=n8n_default     # traefik's network must exist
docker compose -f deploy/join/docker-compose.join-proxy.yml config -q
# 1. the proxy container (traefik picks its labels up by itself, no restart)
docker compose -f deploy/join/docker-compose.join-proxy.yml up -d
docker ps --filter name=org-join-proxy --format '{{.Names}} {{.Status}} [{{.Ports}}]'   # Ports stays empty
docker exec org-join-proxy grep host.docker.internal /etc/hosts                          # = the docker0 address
# 2. the unit
sudo cp deploy/join/org-join.service /etc/systemd/system/
sudo systemctl daemon-reload
# 3. start it
sudo systemctl enable --now org-join
journalctl -u org-join -n 20 --no-pager         # "listening on 172.17.0.1:8791"
ss -ltnH 'sport = :8791'                        # 172.17.0.1:8791 only, never 0.0.0.0 or *
```

### Checks

```bash
curl -fsS https://webhook.mooniex.com/org-join/join.sh | head -3
# 200, script text, the hub URL substituted as https://webhook.mooniex.com/org-join
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' -d '{}' \
  https://webhook.mooniex.com/org-join/sealed          # 403
curl -s -o /dev/null -w '%{http_code}\n' https://webhook.mooniex.com/org-join/nothing   # 404
# From a machine that is NOT Contabo (the Mac): the endpoint must not answer on the public address
curl -m 5 -sS -o /dev/null -w '%{http_code}\n' http://194.233.80.26:8791/org-join/join.sh   # refused or timeout, never 200
```

A 502 or 504 on the first check with a healthy unit means the container cannot reach the docker0
address. The usual cause is a host firewall with default-deny `INPUT` (docker does not open that
path): `curl http://172.17.0.1:8791/org-join/join.sh` on the host works, the container's does not.
Allow the `n8n_default` bridge to that one address and port, nothing wider. If the docker daemon
sets `host-gateway-ip` or a custom `bip`, `host.docker.internal` and docker0 must still be the same
address, and it must sit inside `172.16.0.0/12`, or `join_api` exits 2 and says so in the journal.

### Rollback

```bash
cd /opt/MoonieXHQ/Agents/Core
docker compose -f deploy/join/docker-compose.join-proxy.yml down    # the public route is gone
sudo systemctl disable --now org-join                                # the endpoint stops
```

`/etc/systemd/system/org-join.service` may stay; a disabled, stopped unit does nothing. The
token rows in the hub database are untouched by either step.

## Tailscale pre-auth key

`tools/join_api.py` takes an injectable `TailscaleMinter` (`host -> one-use, tagged pre-auth key`).
It is **not wired**: CEO gate G3 (the Tailscale OAuth client) decides that. Until then `/accept`
returns no key and step 5 requires the machine to be on the tailnet already (it stops with the
exact `tailscale up --hostname <name>` to run).

## Tests

```bash
.venv/bin/python -m pytest -p no:warnings tests/test_w43_join_api.py tests/test_w43_join_scripts.py tests/test_w45_bind.py
```

`tests/test_w45_bind.py` reads the compose file, the unit and `bind-docker0.sh` (run with a fake
`ip`). The container, traefik and systemd themselves are only exercised on Contabo, by the checks above.

Install paths (apt, brew, winget, the tailscale repo) are read and dry-run tested, not executed.
The real drill is W4.7: a fresh container and a fresh Windows box.
