# deploy/join: the node side of `hq join` (Org Mesh W4.3)

One command on a new machine, one tap on the hub side, no login and no secret typed.

```
curl -fsSL https://<hub>/org-join/join.sh | sh -s -- --host <name> [--hq-root <path>]     # Linux, macOS
$env:ORG_JOIN_HOST = '<name>'; iwr -UseBasicParsing https://<hub>/org-join/join.ps1 | iex  # Windows (elevated)
```

**The preferred form has no token in it.** Both scripts ask for the token when it is not given:
`join.sh` on the terminal (`/dev/tty`, `stty -echo`, restored on every way out including ^C and
`die`), `join.ps1` with `Read-Host -AsSecureString` (converted to text in memory only). The token is
then in no shell history (`~/.bash_history`, `~/.zsh_history`, PowerShell's `ConsoleHost_history.txt`)
and in no process argument list (`ps`, `/proc/<pid>/cmdline`). Paste it from the Run Inbox card when
asked. The forms that carry it still work, for a machine with no terminal to ask on:
`curl ... | ORG_JOIN_TOKEN=<t> sh -s -- --host <name>`, `curl ... | sh -s -- --token <t> --host <name>`
(history and `ps`), and on Windows `$env:ORG_JOIN_TOKEN` or
`& ([scriptblock]::Create((iwr -UseBasicParsing https://<hub>/org-join/join.ps1).Content)) --token <t> --host <name>`.
The Windows `iex` form cannot take arguments, so it reads `$env:ORG_JOIN_HOST` (and `ORG_JOIN_HQ_ROOT`).

| File | What it is |
|---|---|
| `join.sh` | POSIX sh, Linux + macOS. `--dry-run` prints the nine steps and changes nothing. Every python it starts runs `-I`. |
| `join.ps1` | Windows PowerShell 5.1, ASCII only. Same steps, same messages. |
| `org-join.service` | systemd unit for the hub endpoint (`tools/join_api.py`) on Contabo (W4.5). Not enabled: `door.sh` starts it (W4.6c). |
| `door.sh` | POSIX sh, root on Contabo. `open [--minutes N]`, `close`, `status`, `approve --host H --fingerprint F`. The door is closed by default (W4.6c). |
| `org_join_role.sql` | The hub Postgres role `org_join` the endpoint connects as, with its grants and row guards (W4.6c F3). |
| `org_join_role.py` | Makes the role's password in memory, runs that SQL with it, prints the role's URL for `put` (W4.6c F3). |
| `bind-docker0.sh` | Start-up wrapper of that unit: exports `JOIN_API_BIND` = the docker0 IPv4 address. |
| `docker-compose.join-proxy.yml` | The socat container and traefik labels that put `/org-join` on the internet (W4.5). |
| `tools/join_api.py` | The endpoint the two scripts talk to. |

## The flow

```
operator (phone)           hub (Contabo)                     new machine                      Mac (provisioner)
  Run Inbox: mint --host X ->  join_tokens row
  token, 15 min            <-
                                                   curl .../join.sh | sh -s -- --host X   (token asked, no echo)
                                                   2 keys (age, deploy, dispatch); installs only the tools they need
                              POST /accept  <---   3 accept: token + age pubkey + deploy pubkey
                              hosts: pending_identity    prints  fingerprint: <last 8 of the age recipient>
                              {host, status} --->      4 install the rest
                                                   5 poll POST /sealed every 15 s: "waiting for approval"
  Run Inbox: approve X, compare the 8 characters
  hq_join approve --host X --fingerprint <8> ------------------------------------------>  hq_join provision X
                              node_secrets.ciphertext <---------------------------------------  (mint Infisical secret,
                              hosts: identity_ready                                              seal to X's age key,
                                                                                                 register deploy key)
                              200 {ciphertext, tailscale_authkey?} --->  6 tailscale up --auth-key
                                                   7 GitHub host keys -> known_hosts, clone (StrictHostKeyChecking=yes)
                                                   8 age -d | infisical_setup.py save X --stdin ; node.yaml
                                                   9 probe
```

Accept comes before the long installs, on purpose (review task-79219f24, F1): the token is used
within seconds of being typed, and the operator sees the node's fingerprint at once. Whoever
holds a leaked token and accepts first shows a different fingerprint than the machine the
operator is sitting at, and the approval (W4.6a, `hq_join approve`) is what stops the hub
provisioning them. Step 2 installs only what the keys and the hub calls need (curl, ssh-keygen,
age, python; on Windows age, and git for its ssh-keygen); step 4 installs the rest.

Steps 5 to 7 are in the order the machine needs them, not the order the nine are listed in the
task: the deploy key only works once the operator approved the node and the Mac provisioned it,
and `save` is a script from the clone. The tailnet (step 6) comes after the wait (step 5) because
the hub hands the pre-auth key out with the sealed answer, which exists only after the approval
(CTO review of task-4d6fe461, F1). Nothing before step 6 needs the tailnet: the installs come
from public package repositories, the hub is called at its public URL, and the clone is over GitHub.

Every step is safe to repeat. After any failure, run the same command again: a token that already
joined this host is recognised through `/sealed`, and keys, clone, venv and node.yaml are kept.

## What each side sees

- The token goes in a request body under TLS. It is never a URL, a header, a file, or a line of
  output. `join.sh` takes it from the hidden prompt, `--token` or `ORG_JOIN_TOKEN` (and unsets the
  variable at once). The hub's endpoint answers `503 {"error":"busy"}` when it is overloaded; the
  scripts then stop with "wait a minute and run the same command again", and the token is not
  used up (a 503 comes before any database work).
- The node's client id and secret exist on the node only as age ciphertext until step 8, where
  `age -d | python | infisical_setup.py save` moves them over pipes. `save` (root, `/etc/infisical`,
  0600) is the only thing that stores them. On Windows one python process does the same chain,
  because a PowerShell pipeline re-encodes and adds CRLF.
- The endpoint answers every token problem with the same `403 {"error":"refused"}`. A wrong
  token, another host's token, an expired one, a used one and "not provisioned" cannot be told
  apart from outside. `/sealed` also stops answering 24 hours after the token was used.
- `CLAUDE_CODE_OAUTH_TOKEN` is not fetched. The node reads it at run time with
  `infisical_setup.py run Org-Node prod --as <host> -- <command>` (W4.6c F2). Org-Node is a project
  of its own, prod only, with that one secret in it. The shared identity `org-node` is a viewer
  there and a member of no other project, so a node can no longer read any Agents-Core secret.

## What root runs, and what `-I` does and does not do (F6)

Steps 8 and 9 run as root (`sudo` on Linux and macOS) and execute files from the user-owned clone:
`tools/infisical_setup.py save`, then `infisical_setup.py run`, which execs the venv's python on
`tools/node_dispatch.py probe`. A user-writable file executed by root is a path from the node's
user (an LLM worker included) to root. `join.sh` now starts every python with `-I` (isolated): no
user site-packages and no `.pth` files, no `PYTHON*` variables, no current directory and no script
directory on `sys.path`. `-B` is added where a root process imports the repo, so root writes no
root-owned `.pyc` into the clone (the `PYTHONDONTWRITEBYTECODE` variable that did that before is
one of the variables `-I` ignores). Because `-I` also drops the current directory, `-m
tools.node_dispatch` cannot find the `tools` package (`No module named 'tools'`, reproduced), so the
probe is started by its path, `.venv/bin/python -I -B "$CORE/tools/node_dispatch.py" probe`; the file
puts the checkout on `sys.path` itself (`sys.path.insert(0, ROOT)`) and imports `lib` as before.

What `-I` does **not** fix: the clone's own code is still user-writable and root still runs it, and
so does any `.pth` in the venv's or Homebrew's own site-packages. Closing that needs a model
change, not a flag (a dedicated `orgnode` user that owns the credential and runs the workers, or
`run` dropping to `SUDO_USER` before exec with `save` run from a root-owned copy). That is a
decision for the CTO and the CEO; the review's F6 wording is "at minimum add `-I`".

## GitHub's host keys (F7)

Before the first clone, step 7 fetches `https://api.github.com/meta` over TLS, takes `ssh_keys`
(checks each against `ssh-ed25519|ecdsa-sha2-nistp256|ssh-rsa` and the base64 shape) and writes
them as `github.com <key>` lines into `$CONF_DIR/known_hosts`, replacing any file an older run left.
The clone and every later `git pull` use `StrictHostKeyChecking=yes` with that file. If the fetch
fails or lists no usable key, the script stops and says so: there is no fallback to `accept-new`.
Run the same command again once `api.github.com` is reachable (the unauthenticated API limit is 60
requests an hour per address).

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

Since W4.6c the endpoint is not installed to run all the time: read "The door" and "Live order"
below first. The unit is copied and never enabled, and the proxy container and the unit are
started by `door.sh open`. The commands here are the manual form of what `open` does, and the
checks to run while the door is open.

```bash
cd /opt/MoonieXHQ/Agents/Core
# 0. look first, nothing changes
ip -4 -o addr show dev docker0                  # inet 172.17.0.1/16, inside 172.16.0.0/12
docker network ls --filter name=n8n_default     # traefik's network must exist
docker compose -f deploy/join/docker-compose.join-proxy.yml config -q
# 1. the unit (NOT `enable`: the door starts it)
sudo cp deploy/join/org-join.service /etc/systemd/system/
sudo systemctl daemon-reload
# 2. open the door (a Run Inbox card: `door.sh open --minutes 5`), then look
docker ps --filter name=org-join-proxy --format '{{.Names}} {{.Status}} [{{.Ports}}]'   # Ports stays empty
docker exec org-join-proxy grep host.docker.internal /etc/hosts                          # = the docker0 address
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
deploy/join/door.sh close      # or a Run Inbox card; proxy down, endpoint stopped, timer cancelled
```

`/etc/systemd/system/org-join.service` may stay; a stopped unit that is not enabled does nothing.
The token rows in the hub database are untouched.

### The unit's sandbox, and the load gate (W4.6b; review F3 and F11)

`org-join.service` carries `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome=yes`,
`PrivateTmp`, `ProtectKernelTunables`, `ProtectKernelModules`, `ProtectControlGroups`,
`RestrictSUIDSGID` and `LockPersonality`, each explained in a comment in the file. There is no
`ReadWritePaths=`: the service writes nothing on disk (hub Postgres over the network, logs to
journald, checkout and `/etc/infisical/contabo.env` read-only). Who the unit runs as, and what it can
reach, is the next sections (F3, closed in W4.6c).

Before `systemctl daemon-reload`, on Contabo: `readlink -f /opt/MoonieXHQ/Agents/Core/.venv/bin/python`
must not start with `/home` or `/root` (`ProtectHome=yes` would hide the interpreter), and
`systemd-analyze verify /etc/systemd/system/org-join.service` must print nothing. After the start,
`systemctl show org-join -p NoNewPrivileges -p ProtectSystem -p ProtectHome` and the two checks in
"Checks" above must still answer.

`tools/join_api.py` lets at most 4 requests be inside their database section at once
(`DB_SLOTS`, a module-level `BoundedSemaphore`). A request that cannot get a slot within 2 s
(`DB_WAIT_S`) is answered `503 {"error":"busy"}` with `Retry-After: 2`. The body is read and
checked before the slot is taken, so a slow client holds none; the 503 depends on load and never
on the token. The socat container's `pids_limit: 128` remains the cap on open connections.

## The door: closed by default (W4.6c, CEO 2026-10-01)

The endpoint is not a service that runs all the time. `org-join.service` is not enabled and has no
`[Install]` section, and the proxy container has `restart: "no"`. While the door is shut, nothing
listens on the docker0 address and traefik has no backend for `/org-join`. A CEO tap on a Run Inbox
card opens it for a few minutes, and it shuts itself.

`deploy/join/door.sh` is POSIX sh and runs as root on Contabo:

| Verb | What it does |
|---|---|
| `open [--minutes N]` | N is 1 to 120 (default 30). Schedules its own close first (`systemd-run --on-active=Nm`, unit `org-join-door-close`, replacing an earlier one), then starts `org-join.service`, then `docker compose up -d` for the proxy. Prints one line, `open until <UTC time>`, only after it has checked that service, proxy and timer are all there. On any failure it shuts everything again and exits 1: it never stays open without a timer. A second `open` moves the close time. |
| `close` | Proxy down, service stopped, timer cancelled, then checks both are down. Prints `closed`. Safe to repeat. Exits 1 and says `NOT closed` when something would not stop. |
| `status` | `closed`, or `open until <UTC time>`. `half open: ...` or `open, no close timer scheduled` mean: run `close`. |
| `approve --host H --fingerprint F` | `hq_join approve` for one pending host (the W4.6a F1 gate). Prints the result line only. H is a host name, F is exactly 8 letters or digits. |

### The cards (what the CTO types, what the CEO taps)

A worker can only ask for a script at a pushed commit, so push first: `<sha>` is the commit on
`origin` that holds this `door.sh`. The executor fetches that sha on Contabo, so what the CEO reads
on the card is what runs.

```bash
cd /Users/gob/MoonieXHQ/Agents/Core        # the Mac; on Contabo: /opt/MoonieXHQ/Agents/Core
python3 tools/ask_run.py create --host contabo \
    --script Agents-Core@<sha>:deploy/join/door.sh \
    --why "open the join door for 30 minutes: <name> is about to join" \
    --expected "open until <UTC time>, 30 minutes from now" \
    -- open --minutes 30

python3 tools/ask_run.py create --host contabo \
    --script Agents-Core@<sha>:deploy/join/door.sh \
    --why "approve <name>: its own screen must show fingerprint <8 characters>" \
    --expected "a JSON line with ok true, the same host and the same fingerprint" \
    -- approve --host <name> --fingerprint <8 characters>

python3 tools/ask_run.py create --host contabo --script Agents-Core@<sha>:deploy/join/door.sh \
    --why "close the join door now" -- close
python3 tools/ask_run.py create --host contabo --script Agents-Core@<sha>:deploy/join/door.sh \
    --why "is the join door open?" --risk green -- status
```

Add `--dry-run` to any of them to print the card without sending it.

**The approve card's `--why` must carry the host name and the 8-character fingerprint.** The
fingerprint is the last 8 characters of the node's public key, printed on the node's own screen by
`join.sh` (W4.6b). The CEO compares the card on the phone with that screen. If they differ, the key
on the hub is not the node's, and the tap must be a refusal. The same two values are in the card's
arguments, so the card shows them twice. No card carries a secret: a join token comes only from the
hidden prompt of `join.sh`.

**Where the script runs from.** The runner may delete its copy when the card ends, and the timer
fires up to two hours later. So `open` copies its own file to `/var/lib/org-join-door/door.sh` (root,
mode 700, made for this) and schedules that copy. When run from a pipe, where there is no file of its
own, it copies the checkout's `deploy/join/door.sh` instead, after checking that file starts with
its own header line. If neither is found, it refuses before starting anything.

**`approve` runs under the full hub role.** It runs `hq_join approve` as `secretary` with `org`, not
as `org_join`: approving is the gate against a stolen token, so the endpoint's role is forbidden to
do it (a row guard, below). The `org` URL is read from Agents-Core prod with the `contabo` identity
and handed to the child in its environment, never on a command line.

## Least privilege for the endpoint (W4.6c F3)

The endpoint is reachable from the internet. It used to run as `secretary`, with every Agents-Core
prod secret in its environment and the full `org` role on the hub. Now:

- **A system user of its own**, `org-join`, that owns nothing and has no shell and no home.
- **One secret**, `ORG_JOIN_DB_URL`, from the `/org-join` folder of Agents-Core prod. No other
  Agents-Core value reaches the process.
- **A database role of its own**, `org_join`, with only the grants below.

`tools/join_api.py` reads `ORG_JOIN_DB_URL`. When only `ORG_DB_URL` is set it exits 2 with one line
that names the variables, unless `JOIN_API_ALLOW_ORG_ROLE=1` says the full role is intended: then it
connects with it and logs a one-line warning (a stopgap for a hub that has no `org_join` yet; the
unit never sets it). When both are set it uses `ORG_JOIN_DB_URL` and warns that `ORG_DB_URL` is
ignored. No message holds a value.

**How the unit gets the machine credential without widening `/etc/infisical`.** The unit starts as
root, because only root can read `/etc/infisical/contabo.env` (0600, unchanged). The root leg is
`bind-docker0.sh`, then `infisical_setup.py run Agents-Core prod --as contabo --path /org-join`,
which logs in and puts only the `/org-join` folder in the environment. Its child is
`setpriv --reuid=org-join --regid=org-join --init-groups`, which drops to the new user and execs the
endpoint. The user `org-join` never sees the credential file or the credential, and no permission on
`/etc/infisical` changes. `setpriv` execs, so systemd still supervises the endpoint's own pid.
`infisical_setup.py run` refuses to start on an empty folder, so a missing `ORG_JOIN_DB_URL` stops
the service with a clear message instead of starting it with no database.

### What the role can do, derived from the SQL

Nothing is granted that one of these statements does not use. The statements are in
`tools/join_api.py` and `tools/hq_join.py`, and the tests read them from there.

| Table | Grant | Used by |
|---|---|---|
| `join_tokens` | `SELECT (token_hash, host, used_at, expires_at)` | the consume, the diagnosis after a failed consume, the `/sealed` token check |
| | `UPDATE (used_at)` | `_CONSUME_SQL`: one atomic `UPDATE ... WHERE used_at IS NULL AND expires_at > ? RETURNING host` |
| `hosts` | `SELECT (host, status)` | `ON CONFLICT (host)`, the rejoin `WHERE`, `RETURNING host` |
| | `INSERT (host, os, hq_root, agents_root, provides, max_workers, status, pubkey, config_json, updated_at, deploy_pubkey)` | `_INSERT_HOST_SQL`, the register |
| | `UPDATE (os, hq_root, agents_root, provides, max_workers, status, pubkey, config_json, deploy_pubkey, approved_at, updated_at, probed_at, free_gb, ram_free_gb, running, version, cpus, load_per_core, runners)` | `_REJOIN_HOST_SQL`, the take-over of a `left` row (`approved_at` and the probe columns go back to NULL) |
| `node_secrets` | `SELECT (host, ciphertext, fetched_at, revoked_at)` | `sealed_ciphertext` |
| | `UPDATE (fetched_at)` | the first-fetch stamp |
| `events` | `INSERT (task_id, actor, kind, payload, ts)` | `db.log_event`: `join_accept`, `node_sealed_fetch` |

Everything else is denied: no `DELETE`, no `TRUNCATE`, no `SELECT` on `pubkey` or `config_json`,
nothing on any other table, no sequence, no `CREATE` in schema `public`. A check at the end of the
SQL compares the role's privileges, column by column, with the list inside the file, and fails the
run when they differ.

`accept` is two statements in one transaction, not one `INSERT ... ON CONFLICT DO UPDATE`: the
second form would need `SELECT` on every column it reads through `excluded`, and the role must not
read `pubkey` or `config_json`. The first statement inserts and does nothing when the name exists;
the second takes over a `left` row only. The loser of a race finds the row `pending_identity`, which
matches neither statement, and gets `host_in_use` with its token un-consumed (the transaction rolls
back).

**Column grants cannot limit rows, so two triggers do, for this role only.** Without them, whoever
held the role's URL could run `UPDATE hosts SET approved_at = now()` (approve their own node) or
overwrite the key of an approved host. `org_join_guard` on `hosts` lets the role write only
`pending_identity` rows with no approval, and update only a row that is `left`. On `events` it lets
the role write only `task_id IS NULL`, actor `hq_join`, kinds `join_accept` and `node_sealed_fetch`.
For every other role the triggers return the row untouched. The role also has `CONNECTION LIMIT 5`,
`statement_timeout 10s` and `idle_in_transaction_session_timeout 15s`; the endpoint lets at most 4
requests into the database section at once and gives each connection back at the end of it.

### Live order (the CTO, and the CEO where it says so)

Do these in this order. Step 2 must come before any node runs under Org-Node, and step 3 before a
node that joined earlier is moved.

1. **Create Org-Node.** `python3 tools/infisical_setup.py plan`, read it, then `apply` (identity
   `setup`, with the CEO's go). It creates the project `Org-Node` (environment `prod` only) and the
   `/org-join` folder in Agents-Core prod. It writes no secret value.
2. **The CEO enters `CLAUDE_CODE_OAUTH_TOKEN` in Org-Node prod** (gate G3). The code never does:
   `put` and `import-env` refuse to write anything else to that project, and the value is typed by
   the CEO in Infisical. Until then `run Org-Node prod` refuses to start, because the folder is
   empty, and so does a node's first probe.
3. **Move the `org-node` membership.** In Infisical: Org-Node, Access Control, Machine Identities,
   add `org-node` as **Viewer**. Then Agents-Core, the same page, remove `org-node`. Add first,
   remove second, so a node that joined earlier is never without the token. Until the removal,
   `apply` prints a `!` line, and every provision refuses (`ensure_node_identity` will not hand a
   node's secret to an identity that can read anything but Org-Node). Existing nodes then run
   `infisical_setup.py run Org-Node prod --as <host> -- <command>`.
4. **Create the role.** On the machine that holds the `setup` credential and can reach the hub
   database, from the checkout, with `psql` installed (`command -v psql`). `org_join_role.py` makes a
   password in memory, runs `org_join_role.sql` with it through the environment (`ps` shows argv, so
   the password is never a `-v` argument), and only when that succeeded prints
   `postgresql://org_join:<password>@<host, port and database of ORG_DB_URL>` on stdout. That line
   goes by pipe straight into `put`, so the password is in no file, no argument and no terminal. The
   connecting role needs `CREATEROLE` (`org` has it; otherwise run it with a `postgres` URL). Running
   it again rotates the password and re-applies the grants. `<id>` is this machine's identity
   (`mac`, `contabo` or `winbox`).

   ```bash
   cd /Users/gob/MoonieXHQ/Agents/Core
   python3 tools/infisical_setup.py run Agents-Core prod --as <id> -- \
       .venv/bin/python deploy/join/org_join_role.py \
     | python3 tools/infisical_setup.py put Agents-Core prod ORG_JOIN_DB_URL --path /org-join --stdin \
         --comment "hub Postgres URL of the org_join role (join endpoint only)" \
         --meta provider_name=org_join --meta console_url=https://terminal.mooniex.com \
         --meta scope=hub-postgres-join-endpoint --meta expires=<YYYY-MM-DD> --meta owner=cto
   ```

   If the script fails it prints nothing on stdout and `put` refuses the empty value. Check the
   result without showing it: `infisical_setup.py last4 Agents-Core prod ORG_JOIN_DB_URL --path /org-join`.
5. **The user.** On Contabo: `id org-join` must say no such user, then
   `sudo useradd --system --no-create-home --shell /usr/sbin/nologin org-join`, then
   `sudo -u org-join test -r /opt/MoonieXHQ/Agents/Core/tools/join_api.py && sudo -u org-join test -x /opt/MoonieXHQ/Agents/Core/.venv/bin/python && echo ok`
   must print `ok`: the user has to read the checkout and run the interpreter, and nothing else.
6. **Install the unit, without enabling it.** `sudo cp deploy/join/org-join.service /etc/systemd/system/`
   and `sudo systemctl daemon-reload`. `systemctl is-enabled org-join` must say `disabled` or
   `static`. Do NOT run `systemctl enable`. If the older always-on version is running, stop it once:
   `sudo systemctl disable --now org-join` and
   `docker compose -f deploy/join/docker-compose.join-proxy.yml down` (the old proxy restarted by
   itself). From then on the door opens from a card, never from a shell.
7. **Try it.** A card `open --minutes 5`, the "Checks" above, then a card `close`, then
   `curl -m 5 -s -o /dev/null -w '%{http_code}\n' https://webhook.mooniex.com/org-join/join.sh`
   must no longer answer 200.

**Rollback.** A `close` card shuts the door at any time. To go back to the W4.6b behaviour (not
recommended): set `JOIN_API_ALLOW_ORG_ROLE=1` and change the unit's `--path /org-join` back to `/`.
The role and the two triggers can stay: they do nothing for any other role.

### What is still open

- `door.sh approve` runs as `secretary` with the full `org` role. A second role for approval only
  would be one more credential to keep; the card and the CEO's tap are what gate it.
- A node that joined before Org-Node read Agents-Core with the old membership. `docs/ops/hq-join.md`,
  "Nodes that joined before Org-Node", says what to rotate when one leaves.
- The door is a schedule, not a lock: while it is open the endpoint answers the internet as it did
  before W4.6c. The token, the rate limit and the approval gate protect that window.

## Tailscale pre-auth key

`tools/join_api.py` takes an injectable `TailscaleMinter` (`host -> one-use, tagged pre-auth key`).
`main()` wires `lib/tailscale_api.py` into it when the Tailscale OAuth client is in the endpoint's
environment (CEO gate G3). **The key is released only after the CEO approves the node's
fingerprint**: `/accept` never carries one, and `/sealed` adds `tailscale_authkey` to its `ready`
answer (the same answer that releases the ciphertext, once the host is approved and its identity
is sealed). Whoever holds a join token but has not been approved gets no key, so a stolen token
alone cannot put a machine on the tailnet. `join.sh` and `join.ps1` run the tailnet step (6)
after the wait (5): `tailscale up --auth-key <key> --hostname <name> --advertise-tags=tag:org-node`
with the key from the sealed answer, and fall back to the old behaviour without one.

| Situation | What the endpoint does |
|---|---|
| Both variables set | The `ready` answer of `/sealed` adds `tailscale_authkey`: one use (`reusable: false`), pre-authorized, `tag:org-node`, not ephemeral, valid 1 hour, described `org-node:<host>`. A new key per `ready` answer; `pending` and every 403 mint nothing; `/accept` never mints. The journal says `(minter wired)`. |
| Neither set | As before: no key field, step 6 requires the machine to be on the tailnet already (it stops with the exact `tailscale up --hostname <name>` to run). The journal says `(minter not wired)`. |
| One without the other | The endpoint refuses to start (exit 2) and names the two variables. Half a configuration must not look like "not configured". |
| Tailscale refuses or is down | The `ready` answer still goes out with the ciphertext and no key field. One journal line, `tailscale minter failed for <host>: TailscaleError (HTTP <status>)` (class name and the integer status only, never a body or a message). The node gets step 6's "join by hand" message; running the same command again polls `/sealed` again and gets a fresh try. |

The client secret, the access token and the minted key are never in a log line, an exception
message or an argument list; the key is in the `/sealed` answer and nowhere else. The only address
the secret is ever posted to is `https://api.tailscale.com`: there is no environment variable
that changes it. `leave` removes the node's device, not its key: a key that was never used (the
node left before step 6, or re-ran the command) dies by itself within the hour. A re-run polls
`/sealed` again (to tell "already joined" from "wrong token") and each `ready` answer mints a key,
so a re-run leaves one unused key that expires within the hour.

### What the CEO sets up (once)

1. **ACL.** In the Tailscale admin console, Access controls, add the tag to `tagOwners`:
   ```
   "tagOwners": { "tag:org-node": ["autogroup:admin"] },
   ```
   If the ACL is not allow-all, tagged nodes also need a rule that lets them reach, and be
   reached by, mac, contabo and winbox.
2. **OAuth client.** Settings, OAuth clients, Generate. Tick exactly two scopes:
   **Auth Keys: Write** and **Devices Core: Write**. When it asks which tags the client may use,
   pick `tag:org-node` and no other. Copy the client ID and the client secret once.
3. **Infisical.** Project **Agents-Core**, environment **prod**, folder **/org-join** (the folder the
   `org-join` unit already injects, `infisical_setup.py run Agents-Core prod --as contabo --path /org-join`),
   two secrets:

   | Name | Value |
   |---|---|
   | `TAILSCALE_OAUTH_CLIENT_ID` | the client ID |
   | `TAILSCALE_OAUTH_CLIENT_SECRET` | the client secret |

   Both pass the PLAN §4b name lint. From a terminal, the value goes on stdin, never into an argument:
   `python3 tools/infisical_setup.py put Agents-Core prod TAILSCALE_OAUTH_CLIENT_SECRET --path /org-join --stdin --comment "<purpose>" --meta provider_name=... --meta console_url=... --meta scope=... --meta expires=... --meta owner=...`
   (PLAN §4c metadata; the Infisical page works as well). No unit change is needed.

The endpoint reads its environment when it starts, so the key takes effect the next time the door
opens (`door.sh open`), not before.

### Check that the minter is wired (no Tailscale call needed)

```bash
journalctl -u org-join -n 40 --no-pager | grep -E 'infisical run|listening on'
```

- `[infisical run] Agents-Core/prod/org-join ... TAILSCALE_OAUTH_CLIENT_ID, TAILSCALE_OAUTH_CLIENT_SECRET ...`
  lists the names the folder injected (never the values).
- `join_api ... listening on 172.17.0.1:8791 (minter wired)`. `(minter not wired)` means neither name
  reached the process; the endpoint did not start at all if only one did.

The first real proof is the first join, after the CEO approves it: the `ready` answer of `/sealed`
carries `tailscale_authkey`, and step 6 prints `joined the tailnet`. If the journal instead shows `tailscale minter failed`, check the two scopes,
the tag the client may use and the `tagOwners` line above.

### What it can do if the endpoint is compromised

The endpoint is public, and it now holds the Tailscale OAuth client secret in memory (before:
only the `org_join` database URL). Whoever gets that secret can mint tagged pre-auth keys, which
add machines to the tailnet as `tag:org-node`, and delete devices. Keep the client at exactly the
two scopes and the one tag above, so it can touch nothing else, and rotate it like any other key
(new client in Tailscale, Infisical, restart the door, delete the old client).

## Tests

```bash
.venv/bin/python -m pytest -p no:warnings tests/test_w43_join_api.py tests/test_w43_join_scripts.py tests/test_w45_bind.py tests/test_w46b_node_fixes.py tests/test_w46c_node_project.py tests/test_w46c_join_role.py tests/test_w46c_door.py tests/test_w47_tailscale.py
ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54330/org_test \
    .venv/bin/python -m pytest -p no:warnings tests/test_w46c_join_role.py   # adds the real-Postgres tests
```

`tests/test_w46c_door.py` runs `door.sh` for real under `dash`, `sh` and `bash`, with `systemctl`,
`docker` and `systemd-run` replaced by shims on disk (it never touches a real systemd). It covers
the timer-first order, the rollback when each step fails, the clamp on minutes, `close` being
repeatable, `status`, the `approve` argument checks, and that no secret reaches argv or output.
`tests/test_w46c_join_role.py` reads the SQL, and runs it against a scratch Postgres when
`ORG_TEST_DB_URL` is set: a real accept and sealed over HTTP as `org_join`, a matrix of denied
privileges, the row guards, the 5-connection limit, re-running, password rotation and drift
detection. `tests/test_w46c_node_project.py` covers Org-Node in `infisical_setup.py` against a fake
Infisical.

`tests/test_w46b_node_fixes.py` covers the W4.6b fixes: accept before install, the fingerprint
line, the hidden token prompt (on a real pty), the pinned `known_hosts`, `-I` on every python call,
the 503 gate and the unit's directives. The PowerShell side is read as text there and parsed only
where `pwsh` is installed (it is not on the Mac).

`tests/test_w45_bind.py` reads the compose file, the unit and `bind-docker0.sh` (run with a fake
`ip`). The container, traefik and systemd themselves are only exercised on Contabo, by the checks above.

Install paths (apt, brew, winget, the tailscale repo) are read and dry-run tested, not executed.
The real drill is W4.7: a fresh container and a fresh Windows box.
