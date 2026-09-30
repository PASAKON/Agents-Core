# hq join / hq leave: the hub side (Org Mesh W4.1)

`tools/hq_join.py` is the part of "1 command + 1 tap" that lives on the hub. It
mints a one-time join token, accepts a new node against it, plans the
revocation when a node leaves, and exports the `hosts` table as `hosts.yaml`.

**Status: built, not live.** Nothing in it calls Infisical, Tailscale, GitHub or
ssh. The live revokers wait for W4.2 and CEO gate G3. Nothing reads the export.
Plan: `~/.claude/plans/glimmering-shimmying-eagle.md` section W4.

## Verbs

Run on the hub host, with the hub environment (`ORG_DB_URL`):

```bash
python -m tools.hq_join mint --host <name> [--ttl-min 15]
python -m tools.hq_join accept --token <t|-> --host <name> --os <darwin|linux|windows> \
                               --hq-root <abs path> --pubkey <age1...>
python -m tools.hq_join leave --host <name> [--live]
python -m tools.hq_join export-hosts [--out PATH]
```

Exit codes: `0` ok, `1` `leave --live` ran and left steps behind, `2` refused
(bad argument, or the token or name was rejected) with nothing changed.

### mint

- `<name>`: 3 to 32 chars, `a-z 0-9 -`, starts with a letter, does not end in `-`.
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
- `leave` refuses a host that has no `pubkey` (mac, contabo, winbox were never
  joined through `accept`): revoking "their" keys on every other host would cut
  the hub off.
- W4.2 will also have to delete the node's sealed-secret ciphertext from the hub
  when it adds that table. Not in this file, because the table does not exist yet.

### export-hosts

- Writes `hosts:` for every row whose status is not `left` or `pending_identity`,
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
  resolves itself through `node.yaml` (join.sh step 5), so this only matters for a
  node that skipped it.

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
- `lib/db_pg.py` is not changed: the declared touches did not include it, and
  the shared DDL constant is run for both backends by `init_schema()`.

## Tests

```bash
.venv/bin/python -m pytest -p no:warnings tests/test_w41_hq_join.py
ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test \
    .venv/bin/python -m pytest -p no:warnings tests/test_w41_hq_join.py   # adds the pg param
```

The single-use test starts 20 accepts on a barrier and requires exactly one `ok`
and 19 `already_used`. `test_probe_a_read_then_write_consume_fails_the_single_winner_check`
swaps the atomic consume for read-then-write and requires that same check to
fail. With the naive version the token check lets all 20 through and the `hosts`
primary key is what stops 19 of them, which is why the assertion insists on
`already_used` and not just "one winner".
