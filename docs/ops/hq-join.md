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
python -m tools.hq_join provision --host <name>      # W4.2, Mac side, needs ORG_W42_PROVISION=1
python -m tools.hq_join sealed --host <name>         # W4.2, prints the armored ciphertext
python -m tools.hq_join leave --host <name> [--live]
python -m tools.hq_join export-hosts [--out PATH]
```

Exit codes: `0` ok, `1` `leave --live` ran and left steps behind, `2` refused
(bad argument, or the token or name was rejected) with nothing changed.

### mint

- `<name>`: 3 to 31 chars, `a-z 0-9 -`, starts with a letter, does not end in `-`.
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
- `leave` refuses a host that has no `pubkey` (mac, contabo, winbox were never
  joined through `accept`): revoking "their" keys on every other host would cut
  the hub off.
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
probe has not measured. `config/hosts.yaml` wins for every name it declares, so
a node.yaml that names `mac` adds nothing to `hosts()`. `self_host()` then resolves in this
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

A row in `pending_identity` becomes `identity_ready` through **one Mac-side call**:

```bash
ORG_W42_PROVISION=1 python -m tools.hq_join provision --host <name>
python -m tools.hq_join sealed --host <name>      # the armored ciphertext, for W4.3 to deliver
```

### Why one shared identity, and no sixth

Infisical Free allows **5 machine identities**. `mac`, `contabo` and `winbox` are
three of them, and `setup` (the admin identity) is the fourth until
`retire-setup`. That leaves one. A new node therefore gets its own **client
secret** under ONE shared identity `org-node` (Universal Auth, viewer on
Agents-Core), never its own identity. `infisical_setup.ensure_node_identity`
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
   `changed: false` and does nothing: re-running is a no-op.
3. **Claim.** One atomic `INSERT ... ON CONFLICT ... RETURNING` puts a
   `node_secrets` row in place before anything is minted. A second run sees it and
   answers `busy` for 10 minutes (`CLAIM_STALE_S`); after that it revokes what the
   dead run left behind and starts again.
4. **Mint** a client secret `org-node:<host>` (no ttl, unlimited uses). Its id is
   written to the claim row **at once**, before anything else can fail.
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
never stops the others.

Caveat for going live: `/etc/infisical` is root-only on the Mac, so the watchdog's
user must be able to **stat** the setup file for `is_admin_host()` to be true. If
it cannot, the pass is silently a no-op: check that before relying on it.

### Schema

```
node_secrets (host PK, ciphertext, infisical_client_secret_id, github_deploy_key_id,
              created_at, fetched_at, revoked_at)          -- lib.db.NODE_SECRETS_SCHEMA
hosts.deploy_pubkey TEXT                                    -- _HOSTS_JOIN_MIGRATION
```

`sealed --host` stamps `fetched_at` the first time it is called (and logs
`node_sealed_fetch`), so the hub can tell whether the ciphertext was ever handed
over. It refuses a host that has no live ciphertext (`not_provisioned`).

### Left for W4.3 and for going live

- **Delivery** of the ciphertext to the node, and the node opening it with its age
  identity. `sealed.open()` exists for that; nothing calls it yet.
- Setting `ORG_W42_PROVISION=1` on the Mac, plus the CEO's go for the first real
  provision (it creates the `org-node` identity and a real client secret).
- `tailscale_device` and `authorized_keys` revokers.
- A real `age` run on the node side. On the Mac, `age` 1.3.2 is installed and the
  real round trip is covered by `test_real_age_round_trip`; it skips where `age`
  is not on PATH.

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
- `lib/db_pg.py` is not changed: the declared touches did not include it, and
  the shared DDL constant is run for both backends by `init_schema()`.

## Tests

```bash
.venv/bin/python -m pytest -p no:warnings tests/test_w41_hq_join.py tests/test_w42_provision.py tests/test_w42_sealed.py
ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test \
    .venv/bin/python -m pytest -p no:warnings tests/test_w41_hq_join.py   # adds the pg param
```

The single-use test starts 20 accepts on a barrier and requires exactly one `ok`
and 19 `already_used`. `test_probe_a_read_then_write_consume_fails_the_single_winner_check`
swaps the atomic consume for read-then-write and requires that same check to
fail. With the naive version the token check lets all 20 through and the `hosts`
primary key is what stops 19 of them, which is why the assertion insists on
`already_used` and not just "one winner".
