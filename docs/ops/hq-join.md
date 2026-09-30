# hq join / hq leave: the hub side (Org Mesh W4.1)

`tools/hq_join.py` is the part of "1 command + 1 tap" that lives on the hub. It
mints a one-time join token, accepts a new node against it, plans the
revocation when a node leaves, and exports the `hosts` table as `hosts.yaml`.

**Status: built, not live.** By default nothing in it calls Infisical, Tailscale,
GitHub or ssh. W4.2 adds the calls (below), but they run only with
`ORG_W42_PROVISION=1` on the admin host, and every outside call is injectable so
the tests never reach a real service. The Tailscale and `authorized_keys` revokers
wait for CEO gate G3 and W2.8. Nothing reads the export.
Plan: `~/.claude/plans/glimmering-shimmying-eagle.md` section W4 (W4.2: "redesign
for Infisical Free").

## Verbs

Run on the hub host, with the hub environment (`ORG_DB_URL`):

```bash
python -m tools.hq_join mint --host <name> [--ttl-min 15]
python -m tools.hq_join accept --token <t|-> --host <name> --os <darwin|linux|windows> \
                               --hq-root <abs path> --pubkey <age1...> [--deploy-pubkey "<ssh-ed25519 ...>"]
python -m tools.hq_join status [--host <name>]       # W4.6a, lists joined nodes + the fingerprint to compare
python -m tools.hq_join approve --host <name> --fingerprint <8 chars>   # W4.6a, the gate before provision
python -m tools.hq_join provision --host <name>      # W4.2, Mac side, needs ORG_W42_PROVISION=1
python -m tools.hq_join sealed --host <name>         # W4.2, prints the armored ciphertext
python -m tools.hq_join leave --host <name> [--live]
python -m tools.hq_join export-hosts [--out PATH]
```

Exit codes: `0` ok, `1` `leave --live` ran and left steps behind, `2` refused
(bad argument, or the token or name was rejected) with nothing changed.

### mint

- `<name>`: 3 to 31 chars, `a-z 0-9 -`, starts with a letter, does not end in `-`.
- **Reserved names (W4.6a F13):** `setup`, `org-node` and every machine identity
  (`mac`, `contabo`, `winbox`: the keys of `infisical_setup.MACHINES`) are refused by
  every verb with `bad_arg`. A joined node named `setup` or `contabo` would have its
  Infisical client secret description, its `authorized_keys` line and its dispatch
  routing collide with the real one. A name that only contains one (`mac-mini`,
  `setup-2`) is fine. `hq_join.reserved_hosts()` is the list; it reads the names from
  `infisical_setup`, which `hq_join` already imported, so no import cycle is added.
- TTL: 15 minutes by default, 1 to 60 allowed.
- A name is free only if it has no `hosts` row or its row is `left`, and it is not
  a key in `config/hosts.yaml`. This is stricter than "online or pending_identity":
  an `offline` host, or a row seeded from `hosts.yaml` that never heartbeated
  (status NULL), keeps its name too, so a token holder cannot take over the
  identity of a host that is only asleep.
- The token is `hqj_` plus 43 url-safe characters (256 bits). It is printed once,
  alone, on stdout. The hub stores only its sha256 (`join_tokens.token_hash`).
  A line on stderr says the host and the expiry time, never the token.
- Audit: one `events` row, kind `join_mint`, payload `{host, expires_at}`.

### accept

- Valid once, before `expires_at`, for the minted host name only.
- The consume is one statement:
  `UPDATE join_tokens SET used_at=? WHERE token_hash=? AND host=? AND used_at IS NULL AND expires_at>? RETURNING token_hash`.
  The `hosts` insert is in the same transaction, so a refusal anywhere rolls the
  consume back and the token stays usable. Same SQL on SQLite and Postgres.
- Arguments are checked before the token is touched: a typo in `--pubkey` does
  not cost the operator a token.
- A rejected call changes nothing and says which reason, without echoing the
  token: `unknown token`, `different host name`, `already used`, `expired`,
  `host name is already registered`.
- On success the row is `hosts.status = pending_identity` with `os`, `hq_root`,
  `agents_root` (`<hq-root>/Agents/Core`), `pubkey`, and `config_json` (the
  hosts.yaml entry: `ssh` is the host name, `provides: []`, `max_workers: 1`,
  `runners: []`, all conservative until the W4.4 probe fills them).
- **`--hq-root` characters (W4.6a F14):** only `A-Za-z0-9`, space and `. _ / \ : -`,
  on top of the existing rules (absolute for the `--os`, no `..`, not a filesystem
  root, no control character, at most 240 chars). The path ends up in commands a
  shell and PowerShell run on the node, so `$`, a backtick, `;`, quotes, `(`, `)`,
  `&`, `|`, `~` and non-ASCII letters (Thai included) are refused. A Windows home
  such as `C:\Users\x (2)\MoonieXHQ` or one with Thai letters does not pass: install
  under a plain path. `lib.config._node_hq_root` applies the same rule to
  `node.yaml` (a test pins the two together).
- The result carries `fingerprint`, the last 8 characters of the node's age
  recipient. The row starts **unapproved** (`hosts.approved_at` NULL): see
  "The approval gate". A rejoin resets `approved_at` to NULL.
- `--token -` reads the token from stdin so it stays out of `ps`.
- `--deploy-pubkey` (W4.2, optional): the node's `ssh-ed25519 <base64>` public key,
  checked by shape (comment dropped, one line only). It is stored in its **own
  column `hosts.deploy_pubkey`**, not in `config_json`, because `config_json` is
  what `export-hosts` writes out and a deploy key has no business in `hosts.yaml`.
  Leaving it out is not an error: the node gets no GitHub deploy key, the CLI
  says so on stderr, and `provision` skips that leg. A bad key is refused before
  the token is touched, like `--pubkey`. A rejoin replaces it.

**Why the node key is an age X25519 recipient (`age1...`), not `ssh-ed25519`.**
W4.2 seals the Infisical client secret to this key, which needs an encryption
key. `age` is needed on both ends either way (sealing on the Mac, opening on the
node), because an ssh-ed25519 key would only work through age's ssh-recipient
conversion, so ssh saves no dependency. An age recipient is a fixed 62-character
bech32 string with a checksum, so a typo is refused here instead of producing a
secret nobody can open; an `authorized_keys` line has options and a comment
field, and a key stored next to code that manages `authorized_keys` invites
someone to paste it there. The node runs `age-keygen` once in join.sh step 3.

### leave

Plans the revocation, in this order:

| step | target | what a real revoker must do |
|---|---|---|
| `infisical_client_secret` | the node | revoke that node's Universal Auth client secret under identity `org-node` (only that one) |
| `tailscale_device` | the node | remove the tailnet device and its pre-auth key |
| `github_deploy_key` | the node | delete the deploy key(s) registered for it |
| `authorized_keys` | each other host that has not left | remove the node's dispatch key and admin pubkey line |

- Without `--live` it prints the plan and changes nothing (no revoker is called,
  no row and no event is written).
- With `--live` each step goes through a revoker. One failed step, or a revoker
  that raises, never stops the others. The row goes to `left` only when every
  step was ok. Otherwise the row keeps its status and the output lists what is
  left behind (`kind:target`). Re-running converges, so a real revoker must be
  idempotent: already gone (404) is ok.
- **`--live` today refuses every step** (`not wired yet: ...`): the shipped table
  is `UNWIRED_REVOKERS`, so the exit code is `1` and the row stays. W4.2 replaces
  the first and third entries, G3 the second, W2.8 the fourth. The interface is
  `Revoker = Callable[[Step], Outcome]`, passed as `leave(..., revokers={...})`.
- **W4.2 wires the first and third rows** when `ORG_W42_PROVISION=1` (see
  "W4.2: per-node identity"). The default table is chosen when `leave` is called
  without `revokers=`: the wired table with the flag, `UNWIRED_REVOKERS` without it.
  `tailscale_device` and `authorized_keys` stay `not wired yet`, so a real
  `leave --live` still ends `partial` (exit `1`) until G3 and W2.8 land.
- `leave` refuses a host that has no `pubkey` (`not_joined`: a row seeded from
  `hosts.yaml` was never joined through `accept`): revoking "their" keys on every
  other host would cut the hub off. mac, contabo and winbox are refused even
  earlier, as reserved names (`bad_arg`).
- **`leave --live` ends with a rotate block (W4.6a F8).** Revoking the client secret
  stops new logins; it does not recall what the node already read. The last lines of
  the output name the secrets to rotate: the NAMES org-node can read (Infisical, read
  just now; the list call returns values and they are dropped, never returned or
  printed), or, when this box has no admin login (`ORG_W42_PROVISION` off, not the
  admin host, or the lookup failed), the documented categories below, labelled as
  such. The block is printed also when the leave ended partial, and never on a dry
  run or for a host that had already left. Procedure: "After a leave: rotate what
  the node could read".
- When the Infisical leg succeeds, `node_secrets.revoked_at` is set and the
  ciphertext is nulled (the client secret id stays, as the audit trail). The
  deploy key id is nulled once the key is deleted. A leg that fails keeps its id
  for the next run.

### export-hosts

- Writes `hosts:` for every row whose status is not `left`, `pending_identity` or
  `identity_ready` (W4.2: a provisioned node has no probe yet, so nothing can be
  routed to it),
  from `hosts.config_json`. `lib.db.seed_hosts_from_config()` now fills
  `config_json` with the whole hosts.yaml entry, and `accept` fills it for a
  joined node.
- Checked against the current file: `yaml.safe_load(export)["hosts"] ==
  lib.config.hosts()` for mac, contabo and winbox, key order inside each entry
  included, and `lib.config` reads the exported file back as the same registry
  (`tests/test_w41_hq_join.py::test_export_round_trips_what_lib_config_reads_today`).
- Host order in the export is alphabetical. No reader depends on order.
- **Default output is stdout.** `--out PATH` writes a file. The export cannot keep
  the long comments in `config/hosts.yaml`, so nothing here overwrites the tracked
  file by default. Switching `lib.config.hosts()` to the hub is a separate task.
- A row with no `config_json` (for example one created only by a heartbeat) makes
  the export refuse, naming the host, rather than emit a half entry.
- Note for the cutover: a second host with the same `os` makes
  `lib.config._platform_host()` ambiguous (it returns None). The joined node
  resolves itself through `node.yaml` (join.sh step 8), so this only matters for a
  node that skipped it.

### How a joined node knows itself

A joined node is in the hub's `hosts` table and never in this repo's
`config/hosts.yaml`, so it learns who it is from its own
`~/.config/mooniex/node.yaml` (`host`, `os`, `hq_root`), which join.sh step 8 and
join.ps1 write. `lib.config.hosts()` adds an entry for it when all three are
well-formed: `host` is 3 to 31 chars (the same rule as `mint`), `os` is one of
`darwin`, `linux`, `windows`, and `hq_root` is an absolute path for that `os`,
with no `..` and not a filesystem root. The entry has `os`, `hq_root`,
`agents_root` (`<hq_root>/Agents/Core`), `worktrees`, `ssh: None`,
`provides: []`, `max_workers: 1` and `runners: []`: nothing is claimed that the
probe has not measured. `hq_root` here follows the same character rule as `accept`
(W4.6a F14: `A-Za-z0-9`, space and `. _ / \ : -` only). `config/hosts.yaml` wins for every name it declares, so
a node.yaml that names `mac` adds nothing to `hosts()`.

**A node.yaml may not relabel a core box (W4.6a F12).** node.yaml is a file in the
service user's home, so whoever can write it could make a core box act as another
core host (reaping, routing). When node.yaml names a host that `config/hosts.yaml`
declares, and this checkout's path is the `agents_root` of a *different* declared
host, `self_host()` raises a `ValueError` that names both and says to remove
node.yaml or correct its host. A checkout that matches no host says nothing, and a
joined node (a name `hosts.yaml` does not declare) is not affected. `self_host()`
then resolves in this
order: `ORG_HOST`, node.yaml `host`, the checkout path, the OS. `ORG_HOST` and
node.yaml resolve a name only if `hosts()` holds it, so a bare `ORG_HOST=<name>`
with no node.yaml to back it raises. That is why join.sh step 9 runs the probe
with `HOME` as well as `ORG_HOST` in its command: under `sudo` the probe would
otherwise see root's home and no node.yaml. A node.yaml that is not well-formed
adds nothing to `hosts()` and `self_host()` reports it. The synthesized entry is
never written to the hub: `lib.db.seed_hosts_from_config()` seeds only what
`config/hosts.yaml` declares, and the hub's row for the node comes from `accept`.

## Run Inbox card for mint

The CEO triggers `mint` by tapping a card on Contabo. Cards are created by a
C-level session (`--command` is refused for a developer role, and there is no
committed wrapper script, so the line below was **not** dry-run here):

```bash
python3 tools/ask_run.py create --host contabo \
    --cwd /opt/MoonieXHQ/Agents/Core --timeout 60 --risk amber \
    --why "mint a one-time join token for new host <name>" \
    --expected "one line starting hqj_, valid 15 minutes, single use" \
    --command "bash scripts/hub/with-org-db-env.sh .venv/bin/python3 -m tools.hq_join mint --host <name>"
```

`with-org-db-env.sh` puts `ORG_DB_URL` in the command's environment (Infisical leg
on Contabo). The card output is the token on stdout plus one line on stderr.

**Residual risk for W4.6:** the card output is stored by the Run Inbox hub and the
finished card is mailed to the requesting session, so the token lands in both
places. It is single use and dies in 15 minutes (or as soon as the node accepts),
and only its hash is in the database, but it does pass through the card and the
requester's mailbox. CLAUDE.md says a secret value never appears in a Run Inbox
card; a one-time, short-lived join token is not a long-lived secret, but W4.6
should rule on it.

## W4.2: per-node identity

A row in `pending_identity` becomes `identity_ready` through **one approval and one
Mac-side call**:

```bash
python -m tools.hq_join status                                   # the fingerprint the hub holds
python -m tools.hq_join approve --host <name> --fingerprint <8 chars from the node's screen>
ORG_W42_PROVISION=1 python -m tools.hq_join provision --host <name>
python -m tools.hq_join sealed --host <name>      # the armored ciphertext, for W4.3 to deliver
```

### The approval gate (W4.6a F1)

`accept` proves the caller held a token, not that the caller is the machine the
operator meant: the first caller with the token wins the name and chooses the age
key the client secret will be sealed to. So a row does not get an identity until a
human says the key is the right one.

- The **fingerprint** is the last 8 characters of the node's age recipient (2 key
  characters and the 6-character bech32 checksum; public, no secret). The node
  must show it on its own screen. **`join.sh` / `join.ps1` do not print it yet**
  (`deploy/join/*` belongs to W4.6b); until they do, read it on the node with
  `age-keygen -y <identity file> | tail -c 9`. `status` (and the `accept` result)
  show the fingerprint the hub stored.
- `approve --host <name> --fingerprint <8 chars>` sets `hosts.approved_at` only when
  the row is `pending_identity` and the fingerprint equals the last 8 characters of
  the stored key (constant-time compare). The fingerprint must be **read off the
  node**, not copied from `status`: copying it from `status` compares the hub's
  value with itself and proves nothing. A mismatch is `fingerprint_mismatch` and the
  message does not echo the stored value; if the two still differ after a re-read,
  someone else used the token: do not approve. Approving twice is a no-op; every
  approval writes one `join_approve` event `{host, fingerprint}`.
- `provision` refuses an unapproved row (`not_approved`) before any login, claim or
  mint. `provision_pending` returns `{host, skipped: "not_approved"}` for it, which
  is not a failure and does not start the one-hour back-off: the next pass after
  `approve` provisions it.
- A rejoin (`accept` over a `left` row) resets `approved_at` to NULL.
  `accept` does this with two statements in one transaction (W4.6c): an INSERT that does
  nothing when the name exists, then an UPDATE `WHERE host = ? AND status = 'left'`.
  One `INSERT ... ON CONFLICT DO UPDATE ... excluded.*` would make Postgres ask for
  SELECT on every column it reads through `excluded`, which the endpoint's role
  (`org_join`) must not have.
- 8 characters are 40 bits. A racer who wants to be approved must *grind* a key
  whose last 8 characters equal the node's, about 2^40 key generations, and cannot
  start before the node has made its key, inside a 15-minute token. That stops a
  racer who simply used the token first; it is not a signature and not a defence
  against an attacker with a large GPU farm and a long token window.

### Why one shared identity, and no sixth

Infisical Free allows **5 machine identities**. `mac`, `contabo` and `winbox` are
three of them, and `setup` (the admin identity) is the fourth until
`retire-setup`. That leaves one. A new node therefore gets its own **client
secret** under ONE shared identity `org-node` (Universal Auth, viewer on
the project **Org-Node** and on no other project, W4.6c F2), never its own identity. `infisical_setup.ensure_node_identity`
finds or creates `org-node` and **refuses to create a sixth identity**: it raises
`IdentityCapError` naming the five that exist. Revoking one node's secret leaves
every other node's secret working.

### What `provision` does, in this order

1. **Gate.** With a live org, `ORG_W42_PROVISION` must be exactly `1` and this
   host must be the admin host (the setup credential file exists; it is checked
   for existence only and never read). Otherwise `not_enabled` / `not_admin_host`,
   exit `2`, and nothing is logged in.
2. **Validate.** The row must exist (`unknown_host`), must have been joined
   (`not_joined`: mac, contabo and winbox have no `pubkey`), and must be
   `pending_identity` (`bad_status`). An `identity_ready` row returns
   `changed: false` and does nothing: re-running is a no-op. A `pending_identity`
   row with `approved_at` NULL is refused (`not_approved`, W4.6a F1).
3. **Claim.** One atomic `INSERT ... ON CONFLICT ... RETURNING` puts a
   `node_secrets` row in place before anything is minted. A second run sees it and
   answers `busy` for 10 minutes (`CLAIM_STALE_S`); after that it revokes what the
   dead run left behind and starts again.
4. **Mint** a client secret `org-node:<host>` (**ttl 90 days**, 7,776,000 s, unlimited
   uses; W4.6a F4). Its id is written to the claim row **at once**, before anything
   else can fail. The identity's own access-token settings and `retire-setup` are
   not touched.
5. **Seal** `{"v":1,"host","client_id","client_secret"}` to `hosts.pubkey` with
   `lib/sealed.py` (age, plaintext on stdin, armored output).
6. **Deploy key**, if `hosts.deploy_pubkey` is set: `gh api
   repos/PASAKON/Agents-Core/keys` POST, title `org-node:<host>`, `read_only: true`.
   Its id is recorded.
7. **Store** the ciphertext and flip the row to `identity_ready` in one
   transaction; one `node_provisioned` event (host only, never a value).

**A failure after step 4 revokes what was made** (the client secret, and the deploy
key if step 6 got that far) and drops the claim, so the row stays
`pending_identity` with no orphan. If the revoke itself fails, the error is
`provision_orphans`, it names `kind:id` for each leftover, and the claim row keeps
the ids so the next run can finish the job. The watchdog waits one hour before
retrying a host that failed.

### The secret value

It exists in memory between step 4 and step 5, and afterwards only inside the age
ciphertext. It is never in argv (age reads stdin), a temp file, a log line, an
event, an exception message, the stdout of any verb, or any database column. Error
text that happens to carry it is scrubbed. `node-secrets` (in
`tools/infisical_setup.py`) lists description, id, created and revoked, never a
value.

### The watchdog pass

`runners/watchdog.py::_provision_identities` (one call in `scan_once`, after the
letter retry) calls `provision_pending()` for every `pending_identity` row. It
does nothing unless the flag is on AND the host is the admin host. One bad row
never stops the others. A row nobody approved is skipped (W4.6a F1) and the pass
says so once per `PROVISION_BACKOFF_S` (an hour) per host, not on every scan; the
line is kept apart from the failure back-off, so approving takes effect on the very
next pass.

**The 90-day secret expires, and nothing re-provisions it yet (W4.6a F4).** A node's
client secret dies 90 days after `provision`. Until a renewal flow exists, the
node's Infisical login starts failing then, and the fix is a manual one: `leave`,
then `mint` / `accept` / `approve` / `provision` again. The date is
`node_secrets.created_at + 90 days`. Put that on a calendar for every joined node.

Caveat for going live: `/etc/infisical` is root-only on the Mac, so the watchdog's
user must be able to **stat** the setup file for `is_admin_host()` to be true. If
it cannot, the pass is silently a no-op: check that before relying on it.

### Schema

```
node_secrets (host PK, ciphertext, infisical_client_secret_id, github_deploy_key_id,
              created_at, fetched_at, revoked_at)          -- lib.db.NODE_SECRETS_SCHEMA
hosts.deploy_pubkey TEXT                                    -- _HOSTS_JOIN_MIGRATION
hosts.approved_at   TEXT  (nullable, ISO-8601 UTC)          -- _HOSTS_JOIN_MIGRATION, W4.6a F1
```

`sealed --host` stamps `fetched_at` the first time it is called (and logs
`node_sealed_fetch`), so the hub can tell whether the ciphertext was ever handed
over. It refuses a host that has no live ciphertext (`not_provisioned`).

### After a leave: rotate what the node could read

`leave --live` revokes the node's client secret, its deploy key and its
`authorized_keys` lines. That stops the node from logging in again. It does **not**
recall a value the node already read, and the shared identity `org-node` is a viewer
on **Org-Node** (prod only; on Free a viewer sees every environment of a project it is
in, so what counts is what the project holds: one secret, `CLAUDE_CODE_OAUTH_TOKEN`).
So after every `leave --live`, treat what the node could read as seen by whoever holds
the node, and rotate it. The command prints the list as its last lines (names only,
never a value).

Procedure, per name:

1. Make a new key or password **at the provider** (never reuse the old value).
2. Put it in Infisical (`infisical_setup.py`, the project and env the name is in).
3. Restart what reads it, and check the service still works with the new value.
4. Revoke the old one at the provider.
5. If a value ever appeared in chat, a log or a card, tag it `leaked` in Infisical
   first (CLAUDE.md, "Secrets").

The documented set, used when this box cannot ask Infisical (no admin login; the
block says so), is one line since W4.6c: `CLAUDE_CODE_OAUTH_TOKEN (shared by every
node)`, the only secret Org-Node holds. A name that is not on it can still be
readable if someone put it in Org-Node by hand (`put` and `import-env` refuse to), so
prefer the list Infisical gives.

#### Nodes that joined before Org-Node

Until the `org-node` identity was moved (live step 2 in `deploy/join/README.md`,
"Live order"), it was a viewer on **Agents-Core**, and every node that joined before
that read Agents-Core `dev` and `prod` with it. For such a node, `leave --live` still
has to rotate what it could read then, and the documented categories are these (names
move; a name not listed can still have been readable, so prefer a list taken from
Infisical before the move):

- `ORG_DB_URL`: the hub Postgres URL (role `org`).
- `CLAUDE_CODE_OAUTH_TOKEN`: one token shared by every node.
- Run Inbox tokens.
- SomPong / secretary credentials.
- Jules and Jev keys, and the OpenRouter key.
- The Drive OAuth client, and each machine's Drive token.
- LungNote MCP client credentials.

Not covered: a secret that sits in a **folder** below `/` (the lookup reads `/`
only; Org-Node holds no folders, and the `/org-join` folder of Agents-Core prod is in a
project `org-node` is not a member of), and anything the node copied out of the repo
checkout itself.

A node whose start command still names the project Agents-Core (`infisical_setup.py run`
with Agents-Core, prod and its own `--as`) must change the project to Org-Node when the
membership moves: `run Org-Node prod --as <host>` is the form `join.sh` and `join.ps1` print. Until the CEO has entered
`CLAUDE_CODE_OAUTH_TOKEN` in Org-Node prod (gate G3), `run Org-Node prod` refuses to
start, because it refuses an empty folder: do the move and the entry in one sitting.

### Left for W4.3 and for going live

- **Delivery** of the ciphertext to the node, and the node opening it with its age
  identity. `sealed.open()` exists for that; nothing calls it yet.
- Setting `ORG_W42_PROVISION=1` on the Mac, plus the CEO's go for the first real
  provision (it creates the `org-node` identity and a real client secret, and gives it
  viewer on Org-Node; `apply` must have created Org-Node first).
- `tailscale_device` and `authorized_keys` revokers.
- A real `age` run on the node side. On the Mac, `age` 1.3.2 is installed and the
  real round trip is covered by `test_real_age_round_trip`; it skips where `age`
  is not on PATH.

## The door, the endpoint's role and Org-Node (W4.6c)

Three changes from the security review task-79219f24 (F2, F3) and the CEO's ruling of
2026-10-01, "the door is closed by default". They are described where they run, in
`deploy/join/README.md`; in short:

- **The door.** `deploy/join/door.sh open [--minutes N]` starts the endpoint and its
  proxy and schedules their close (default 30 minutes, at most 120); `close`, `status`
  and `approve --host H --fingerprint F` are the other verbs. Each is a Run Inbox card
  on Contabo, so the CEO's tap opens the door, and the door shuts itself. `approve` is
  the W4.6a F1 gate from a card: the card's `--why` carries the host name and the
  8-character fingerprint, which the CEO compares with the node's own screen.
- **F2, Org-Node.** Nodes read the project `Org-Node` (prod only, one secret) and no
  longer Agents-Core. `infisical_setup.py plan` and `apply` create it; `ensure_node_identity`
  refuses, changing nothing, while `org-node` is still a member of any other project; `put` and `import-env` refuse anything in Org-Node but
  `CLAUDE_CODE_OAUTH_TOKEN`.
- **F3, least privilege.** `tools/join_api.py` connects as the Postgres role `org_join`
  (`deploy/join/org_join_role.sql`: column grants on `hosts`, `join_tokens`,
  `node_secrets` and `events`, five connections, row guards) from `ORG_JOIN_DB_URL` in
  the `/org-join` folder of Agents-Core prod, runs as the system user `org-join`, and
  refuses the full role `org` unless `JOIN_API_ALLOW_ORG_ROLE=1`. Approval stays with
  the full role: `door.sh approve` runs `hq_join approve` as before.

## Open for W4.3

`accept` needs write access to the hub, and a joining node has no `ORG_DB_URL`
at step 6 (it arrives from Infisical at step 8). The transport for `accept`
(a forced-command ssh key on the tailnet, or a small endpoint) is W4.3's
decision; W4.1 gives it the in-process `accept()` and the CLI.

## Schema

- New table `join_tokens (token_hash PK, host, created_at, expires_at, used_at)`,
  created by `lib.db.init_schema()` on both backends from one DDL string,
  `lib.db.JOIN_TOKENS_SCHEMA`. `locks` could not hold it: no `used_at`, no
  `host`, and its expired rows are purged, which would turn "expired" and
  "reused" into "unknown" (IRON-RULES section 30: extend before create).
- `hosts` gains `pubkey` and `config_json` (forward-only `ALTER TABLE ADD COLUMN`
  through `_HOSTS_JOIN_MIGRATION`, a list of its own next to the probe's
  `_HOSTS_MIGRATION`, which `tests/test_h1_node_probe.py` pins to exactly its
  three columns; the same loop covers Postgres).
- W4.2 adds `node_secrets` (same pattern: one DDL string, `NODE_SECRETS_SCHEMA`,
  run on both backends) and `hosts.deploy_pubkey` (forward-only, same loop).
- W4.6a adds `hosts.approved_at` (nullable, same loop and the same Postgres
  translation of `PRAGMA table_info`; `lib/db_pg.py` is still not changed). It is in
  `_HOST_COLUMNS`, so `upsert_host` can set it, and `accept` resets it on a rejoin.
- `lib/db_pg.py` is not changed: the declared touches did not include it, and
  the shared DDL constant is run for both backends by `init_schema()`.

## Tests

```bash
.venv/bin/python -m pytest -p no:warnings tests/test_w41_hq_join.py tests/test_w42_provision.py tests/test_w42_sealed.py tests/test_w46a_hub_fixes.py tests/test_w46c_node_project.py tests/test_w46c_join_role.py tests/test_w46c_door.py
ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test \
    .venv/bin/python -m pytest -p no:warnings tests/test_w41_hq_join.py   # adds the pg param
```

The single-use test starts 20 accepts on a barrier and requires exactly one `ok`
and 19 `already_used`. `test_probe_a_read_then_write_consume_fails_the_single_winner_check`
swaps the atomic consume for read-then-write and requires that same check to
fail. With the naive version the token check lets all 20 through and the `hosts`
primary key is what stops 19 of them, which is why the assertion insists on
`already_used` and not just "one winner".
