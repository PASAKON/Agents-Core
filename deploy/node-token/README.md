# Node token service (Org Mesh W4.2b)

The hub hands the CEO's Claude OAuth token to a joined node. A node has no Infisical identity, so it
asks the hub; the hub answers only an approved node and only sealed to that node's own age key.

CEO ruling, 2026-10-03 (`task-edc8d76f`): Infisical Free allows 5 identities and the org already
holds 5, because the CEO's own user account counts (the CEO, `contabo`, `mac`, `winbox`, `setup`).
So `org-node` can never be created, and the fifth slot stays free for KeyFetch's write identity once
`setup` retires (2026-10-10).

- **R1** No new identity. `contabo` becomes a viewer of the project `Org-Node`.
- **R2** The hub hands the token only to a node the CEO approved.
- **R3** The token is never written to a file on the node.
- **R4** A node that has left can never get it again.
- **R5** This is an exception for nodes only to "a service reads its secrets through `infisical
  run`". The hub itself still reads the token through `infisical run`.

Nothing in this folder has been run. Every live step below is a card the CEO taps (or a line the CTO
types); none was executed while building it.

## What is here

| File | What it is |
|---|---|
| `org-node-token.service` | The systemd unit. Enabled at boot, always on (unlike the join door). |
| `bind-tailnet.sh` | First thing the unit runs: exports `NODE_TOKEN_BIND` = this machine's tailnet IPv4 (`tailscale ip -4`). No tailnet address, no start. |
| `org_node_token_role.sql` | The hub role `org_node_token`: `SELECT (host, status, pubkey, approved_at) ON hosts` and nothing else; 24-character-minimum password, `CONNECTION LIMIT 3`, `statement_timeout 5s`. |
| `org_node_token_role.py` | Makes the password in memory, runs the SQL, prints the role's URL on stdout only when it succeeded (for `put`). |
| `tools/node_token_api.py` | The service (stdlib `http.server`, the shape of `tools/join_api.py`). |
| `tools/node_token.py` | The node's side: `python3 -I tools/node_token.py run -- <command>`. |

## What the unit runs

```
bind-tailnet.sh                                   exports NODE_TOKEN_BIND (the tailnet IPv4); fails if there is none
 -> infisical_setup.py run Agents-Core prod --as contabo --path /node-token
                                                  ORG_NODE_TOKEN_DB_URL (the folder holds that one value)
   -> infisical_setup.py run Org-Node prod --as contabo
                                                  CLAUDE_CODE_OAUTH_TOKEN (Org-Node holds exactly that name)
     -> setpriv --reuid=org-node-token --regid=org-node-token --init-groups
       -> python -m tools.node_token_api --port 8792
```

The first two legs run as root, because only root reads `/etc/infisical/contabo.env`; `setpriv` then
drops to the system user `org-node-token`, so the machine credential never reaches the service. The
service listens on the tailnet address only (`100.64.0.0/10`): it refuses `0.0.0.0`, loopback and
any public address, and exits 2 if `CLAUDE_CODE_OAUTH_TOKEN` or `ORG_NODE_TOKEN_DB_URL` is missing.
It copies the DSN into its own `ORG_DB_URL` and never falls back to the full hub URL.

`GET /v1/token?host=<H>` answers `200 {"ciphertext": "<armored age>"}`: the token sealed to the age
recipient in `hosts.pubkey` (`lib.sealed.seal`). Only `H`'s identity, on `H`, opens it. A `403` carries
a short code and nothing else:

| Code | When |
|---|---|
| `unknown_host` | no such host, or a row with no `pubkey` |
| `left` | the status is `leaving` or `left` (R4: `leave` sets `leaving` as its first step) |
| `not_approved` | `approved_at` is empty |
| `not_issuing` | any other status: `pending_identity`, `offline`, empty, or one this code has never seen |

Issuing statuses are `identity_ready` and `online`, with `approved_at` set. `400` is a bad host, name or
nonce (`bad_nonce`: not 32 lower-case hex characters), `429` the rate limit (every request counts against
its source address; only a request that will be granted counts against its host, so a peer cannot spend
another host's window by naming it), `503 busy` the database gate, `503 hub_unavailable` the hub database
does not answer (the service never decides from the read-only ledger snapshot `lib.db` falls back to, and
`/health` says `db: false`), `500 internal` anything unexpected (the class name only is logged). The journal gets one line per answer:
`issued CLAUDE_CODE_OAUTH_TOKEN to <host>`. No log line, error body or `/health` answer holds the
value, a length or its last four characters.

## The cards, in the order they must run

All are typed by the CTO (`--command` is for C-level roles only) and tapped by the CEO. `<sha>` is a
commit on `origin` that holds this folder; `<worktree>` is the detached worktree of `origin/main`
that the Contabo CTO made for it (the live checkout on Contabo can be far behind, see
`docs/ops/join-drill.md`, "Which code runs"). Add `--dry-run` to print a card without sending it.

**Before card 1:** the live checkout the unit runs from, `/opt/MoonieXHQ/Agents/Core`, must contain
this commit. `test -f /opt/MoonieXHQ/Agents/Core/tools/node_token_api.py` must succeed, or card 5
installs a unit that cannot start.

The four things the design names, in dependency order: **Infisical apply** (cards 1, 2), **role** and
**DSN `put`** (card 4, one line: the URL holds the password and never rests on a file, so the role
script's stdout goes by pipe straight into `put`), **unit install and start** (card 5).

1. Free look, changes nothing: what `apply` will do.

   ```bash
   python3 tools/ask_run.py create --host contabo --risk green \
       --script Agents-Core@<sha>:tools/infisical_setup.py \
       --why "W4.2b: show what apply would change (contabo viewer on Org-Node, folder /node-token). Read-only." \
       --expected "plan lists: contabo -> Org-Node viewer, Agents-Core prod folder /node-token. No identity is created." \
       -- plan
   ```

2. **Infisical apply** (identity `setup`, which exists on Contabo as `/etc/infisical/setup.env`). Makes
   `contabo` a viewer of Org-Node, creates the `/node-token` folder in Agents-Core prod. Creates no
   identity and writes no secret value; safe to run again.

   ```bash
   python3 tools/ask_run.py create --host contabo --risk amber \
       --script Agents-Core@<sha>:tools/infisical_setup.py \
       --why "W4.2b (CEO ruling 2026-10-03): contabo reads project Org-Node so the hub can hand the Claude token to approved nodes. No new identity." \
       --expected "apply output names the Org-Node membership and the /node-token folder; no error" \
       -- apply
   ```

3. **The CEO's own step, not a card** (gate G3): enter `CLAUDE_CODE_OAUTH_TOKEN` in Infisical, project
   **Org-Node**, environment **prod**. No code writes that value, and `put` refuses to write anything
   else into that project. Skip it if the value is already there. Until it is, the unit refuses to start.

4. **Role and DSN `put`**: one line. It runs `org_node_token_role.py` with the connecting URL
   (`ORG_DB_URL`, injected by `infisical_setup.py run`), and only when that succeeded stores the role's
   URL as `ORG_NODE_TOKEN_DB_URL` in Agents-Core prod, folder `/node-token`. If the script fails it prints
   nothing and `put` refuses the empty value. Running it again rotates the role's password and
   re-applies the grants. Replace `<YYYY-MM-DD>` with the expiry the CEO picks.

   ```bash
   python3 tools/ask_run.py create --host contabo --risk red --cwd <worktree> \
       --why "W4.2b: create the hub role org_node_token (SELECT on four columns of hosts, nothing else) and store its URL as ORG_NODE_TOKEN_DB_URL in Agents-Core prod /node-token" \
       --expected "one line from put: ORG_NODE_TOKEN_DB_URL, its last four characters, the expiry. No URL printed." \
       --command "python3 tools/infisical_setup.py run Agents-Core prod --as contabo -- .venv/bin/python deploy/node-token/org_node_token_role.py | python3 tools/infisical_setup.py put Agents-Core prod ORG_NODE_TOKEN_DB_URL --path /node-token --stdin --comment 'hub Postgres URL of the org_node_token role (node token service only)' --meta provider_name=org_node_token --meta console_url=https://terminal.mooniex.com --meta scope=hub-postgres-node-token-service --meta expires=<YYYY-MM-DD> --meta owner=cto"
   ```

   Check it without showing it, afterwards:
   `infisical_setup.py last4 Agents-Core prod ORG_NODE_TOKEN_DB_URL --path /node-token`.

5. **Unit install and start.** Creates the system user once, checks it can read the checkout and run
   the interpreter, installs the unit, and starts it now and at boot. A new unit is not a restart of
   anything, but the Contabo rule still applies: before any later restart of a service there, look where
   the tmux server lives (`CLAUDE.md`, "Contabo, one tmux server holds every session").

   ```bash
   python3 tools/ask_run.py create --host contabo --risk red --cwd <worktree> \
       --why "W4.2b: install and start org-node-token.service (the hub hands the Claude token, sealed, to approved nodes; tailnet address only, port 8792)" \
       --expected "active (running); GET /health on the tailnet address answers ok true, token_loaded true, db true" \
       --command "id org-node-token >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin org-node-token; setpriv --reuid=org-node-token --regid=org-node-token --init-groups -- test -r /opt/MoonieXHQ/Agents/Core/tools/node_token_api.py && setpriv --reuid=org-node-token --regid=org-node-token --init-groups -- test -x /opt/MoonieXHQ/Agents/Core/.venv/bin/python && cp deploy/node-token/org-node-token.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now org-node-token && sleep 5 && systemctl is-active org-node-token"
   ```

6. Health, free and read-only (what `GET /health` answers is booleans only):

   ```bash
   python3 tools/ask_run.py create --host contabo --risk green \
       --why "W4.2b: is the node token service up, and does it hold the token and reach the hub database?" \
       --expected "one JSON line: ok, token_loaded and db are all true (booleans only, never a value)" \
       --command 'curl -fsS -m 5 http://$(tailscale ip -4 | head -n 1):8792/health'
   ```

   No answer at all, with the unit failed, usually means Org-Node prod has no `CLAUDE_CODE_OAUTH_TOKEN`
   (step 3): the service exits 2 naming the variable rather than serve an empty token (`token_loaded:
   false` is the same fault, should it ever be seen). `db: false` means the role or its URL is wrong
   (card 4). The unit's own log: `journalctl -u org-node-token -n 40 --no-pager`.

### Where `provision` learns the address

`hq_join provision` seals a bundle `{"v":2,"host":H,"token_url":URL}` to the node and refuses without
`URL`, naming `ORG_NODE_TOKEN_URL`. Set it for whoever runs `provision` (the Mac, the watchdog, the
drill), next to `ORG_W42_PROVISION=1`:

```
ORG_NODE_TOKEN_URL=http://<the hub's tailnet address>:8792/v1/token
```

The address is `tailscale ip -4` on Contabo. It is not a secret, and it is the only thing a node's
`node.yaml` learns about the hub's side (`token_url`). Only that exact shape is accepted: `http://`, an IPv4
address inside `100.64.0.0/10` (written without leading zeros), a port, and the path `/v1/token`. A host name
(MagicDNS too), a public or loopback address, `https`, another path, a user, a query or a fragment is
refused as `bad_token_url` by `provision`, and again by the node (exit `2`) before it asks. A name would
put the request (and the node's host name) at the mercy of whatever answers a DNS lookup.

### Tailnet ACL note (write it, do not apply it)

The service is reachable only on the tailnet. If the tailnet policy is **not** allow-all, `tag:org-node`
needs an `accept` rule to the hub's token port, for example:

```json
{ "action": "accept", "src": ["tag:org-node"], "dst": ["<the hub's tag or tailnet address>:8792"] }
```

Without it a node's probe says `node_token: hub not reachable (URLError)` after three tries. Nothing
here applies that rule: it is the CEO's policy file.

## From a node

```bash
python3 -I /opt/MoonieXHQ/Agents/Core/tools/node_token.py run -- claude -p "hello"
```

`node_token.py` reads `host`, `token_url` and `age_identity` from `~/.config/mooniex/node.yaml` (what
`join.sh` step 8 wrote), asks the hub, opens the answer with `age -d -i <identity>` through pipes, puts
the value in the **child's** environment under `CLAUDE_CODE_OAUTH_TOKEN` (`--name` for another name in
`NODE_SECRET_NAMES`), and replaces itself with the command. The value is never a file, a log line, an
argument or a line of output. Exit codes: `2` bad usage or `node.yaml`, `3` the hub refused (`403`: not
approved, or left), `4` the hub or the network failed, `5` the answer could not be opened, `127` the
command could not start.

Each run sends `?host=<H>&nonce=<16 random bytes, hex>`. The service seals the nonce into the answer
next to `issued_at`, and the node refuses (exit `5`) an answer that does not carry its own nonce or whose
`issued_at` is more than 300 s from its clock. So an old sealed answer, recorded and played back, opens
with the node's key and is still refused. A node whose clock is more than 5 minutes out gets exit `5` and
a message that says to check the clock.

A node that has left cannot ask again: `leave` sets the row to `leaving` before it does anything else
(the service answers `403 left` at once), and the row becomes `left` only when every step succeeded,
so a half-finished leave still stops the token. If that first step cannot be written (the hub database
is down), `leave` runs no other step and reports every step as left behind.

## Known limits

- **The answer is sealed, not signed.** Only the node can read it, but the node cannot tell who sealed
  it: a node's age recipient is not secret, so anyone who can answer a request can seal a payload for
  it. The nonce and `issued_at` stop the replay of an OLD hub answer. They do not stop a process that
  binds the hub's tailnet address on port 8792 while the service is down (the port is above 1024, so
  any local user on the hub can) from answering a node's request with a token **of its own choosing**:
  the node's `claude` runs would then go to the attacker's account. It cannot read the CEO's token
  (the node's request holds none, and it never has the token). The window is the time the service is
  down, and a unit that trips its start limit stays down until `systemctl reset-failed
  org-node-token`. Closing it needs the node to check a signature from a hub key pinned at join, or
  a listening socket that systemd owns. Neither is built. The CTO reports it to the CEO.
- **The service does not know who is calling.** It answers by host name and seals to that host's key;
  it does not tie the caller's tailnet address to the host row (the drill container reaches it over
  the docker bridge, so that would fail there). The tailnet ACL (note above) is the only wall around
  who may ask. Binding the caller to the row with `tailscale whois` is a follow-up, not built.

## Tests

```bash
.venv/bin/python -m pytest -p no:warnings tests/test_w42b_node_token_api.py tests/test_w42b_node_token.py \
    tests/test_w42b_node_token_role.py tests/test_w42b_node_token_cards.py
ORG_TEST_DB_URL=postgresql://org@127.0.0.1:54329/org_test \
    .venv/bin/python -m pytest -p no:warnings tests/test_w42b_node_token_role.py   # adds the real-Postgres tests
```

They run the real service on loopback (`allow_loopback=True`, a constructor argument that `main()` never
passes) with real `age`, and prove: every refused status gets `403` and the sealer is never called; the
answer opens with the node's key and not with a second key; a non-tailnet bind and a missing variable
stop the service; no body, header or log line holds the value; the client writes no file; and, against
a scratch Postgres, the role can read the four columns and no more.
