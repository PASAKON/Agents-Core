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
| `org-join.service` | systemd unit for the hub endpoint (`tools/join_api.py`) on Contabo. **Not installed.** |
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

## Running the endpoint (not done by W4.3)

```bash
# on Contabo, after the W4.6 review and with the W4.5 traefik route ready
sudo cp deploy/join/org-join.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now org-join
```

The unit binds `127.0.0.1:8791` only and runs the endpoint as `secretary`, after root has
fetched the hub database URL from Infisical. W4.5 adds two `Environment=` lines:

```
JOIN_API_PUBLIC_URL=https://<the public hub name>   # what join.sh is told it came from
JOIN_API_TRUST_FORWARDED=1                          # rate-limit per caller, not per traefik
```

`JOIN_API_PUBLIC_URL` matters: without it the hub address in `join.sh` comes from the request's
`Host` header, which is right for a test and not something to trust in production.

## Tailscale pre-auth key

`tools/join_api.py` takes an injectable `TailscaleMinter` (`host -> one-use, tagged pre-auth key`).
It is **not wired**: CEO gate G3 (the Tailscale OAuth client) decides that. Until then `/accept`
returns no key and step 5 requires the machine to be on the tailnet already (it stops with the
exact `tailscale up --hostname <name>` to run).

## Tests

```bash
.venv/bin/python -m pytest -p no:warnings tests/test_w43_join_api.py tests/test_w43_join_scripts.py
```

Install paths (apt, brew, winget, the tailscale repo) are read and dry-run tested, not executed.
The real drill is W4.7: a fresh container and a fresh Windows box.
