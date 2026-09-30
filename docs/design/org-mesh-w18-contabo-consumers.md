# Org Mesh W1.8 — how Contabo's ledger consumers reach the hub (2026-09-30)

Plan row: `~/.claude/plans/glimmering-shimmying-eagle.md` §W1.8. The plan was written before the
Infisical rules (CLAUDE.md §Secrets, CEO 2026-09-25/26). Its line "a group-readable env copy and an
`EnvironmentFile`" would create a new `.env`, so it is replaced here by `infisical run`.

## Facts measured today

| fact | how |
|---|---|
| `lib/db.py` switches to Postgres as soon as `ORG_DB_URL` is in the process env (`_org_db_url`, `lib/db.py:299`) | read |
| `mooniex-secretary`: `User=secretary`, `/usr/bin/python3 runners/secretary_server.py`, EnvironmentFiles `/home/secretary/.secretary.env` + `/etc/mooniex/secretary-secrets.env`, no hardening | `systemctl cat` |
| `mooniex-secretary-waker`: same user and EnvironmentFiles, venv python `-m runners.secretary_waker` | `systemctl cat` |
| `/usr/bin/python3` on Contabo has no `psycopg` | import probe |
| The venv works as user `secretary`: `psycopg` 3.3.6, `requests`, `zoneinfo` import | `runuser -u secretary -- .venv/bin/python -c ...` |
| Neither secretary unit is tracked in the repo (only a 09-24 blueprint copy under `state/`) | `git ls-files` |
| `tools/infisical_setup.py run` fetches the project's secrets and `os.execvpe`s the command; it refuses to start when the folder is empty | read, `:568` |
| The Contabo identity file is root 0600, and the identity reads `Agents-Core` (`:88`) | runbook + code |
| Precedent: `mooniex-line-queue.service.d/infisical.conf` (clears `EnvironmentFile`, `ExecStart` through `run`, `User=root`) | `cat` |
| Which key names `/root/.config/mooniex/org-db.env` holds | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` only, no `ORG_DB_URL` (CTO, 2026-09-30) |

## Consequence: nothing is installed before the cutover window

Because `ORG_DB_URL` is the switch, any unit that gets it starts writing to Postgres at once, while
the rest of Contabo stays on `state/tasks.db`. W1.8 therefore **builds and tests** the pieces and
installs nothing. The installer runs inside G1 (W1.10), next to `cutover-mac.sh`.

## The secret

- `ORG_DB_URL` goes into Infisical `Agents-Core/prod`. Import it with `import-env Agents-Core prod
  /root/.config/mooniex/org-db.env --only ORG_DB_URL --legacy`, on the box, from the file, so nobody sees the value. Verify
  with `last4`. The name stays `ORG_DB_URL` (legacy metadata, as with `VPS_QUEUE_DB`) because
  `lib/db.py` reads that name; rename in PLAN §6 phase 6.
- The URL must reach Postgres from Contabo itself. If the file holds only the hub's own password,
  the value to store is built on the box (for example, the tailnet address the Mac already uses), again without being printed.
- The existing file is never extended (CLAUDE.md §Secrets). It stays for 7 green days (the line-queue
  rule), then goes. `org-snapshot.service` still names it (open item below).

## The units (drop-ins, tracked under `deploy/systemd/<unit>.d/org-db.conf`)

- **watchdog** (root): `ExecStart=` cleared, then `ExecStart=/usr/bin/python3 tools/infisical_setup.py
  run Agents-Core prod --as contabo -- <venv python> -m runners.watchdog --loop`. No `EnvironmentFile`.
- **secretary** and **secretary-waker** (user `secretary`): the identity file is root-only, so the
  fetch runs privileged, then drops to the service user before the service starts:
  ```
  [Service]
  Environment=HOME=/home/secretary
  ExecStart=
  ExecStart=+/usr/bin/python3 /opt/MoonieXHQ/Agents/Core/tools/infisical_setup.py run Agents-Core prod --as contabo -- /usr/bin/setpriv --reuid=secretary --regid=secretary --init-groups -- /opt/MoonieXHQ/Agents/Core/.venv/bin/python /opt/MoonieXHQ/Agents/Core/runners/secretary_server.py
  ```
  `+` runs only that command with full privileges. `setpriv` execs, so systemd still supervises
  the service's own pid. The secretary also moves from `/usr/bin/python3` to the venv. This needs no apt
  package, and the venv is already the waker's interpreter. The two existing `EnvironmentFile` lines
  stay untouched: they are not extended, and moving them is PLAN §6 phase 3.
- **C-level MCP servers on Contabo**: the W1.6 switch, `org_db: hub` in `/root/.config/mooniex/node.yaml`,
  written in step 8 of the cutover, after the migration (see the installer section).
  The wrapper gets `ORG_DB_URL` from `infisical run` when the env file lacks it.

## The installer: `scripts/hub/contabo-cutover-remote.sh` steps 4, 5 and 8 (no new script)

The Contabo half of the cutover already exists and runs inside G1 (W1.10), so the installer is its
steps 4, 5 and 8, not a new script (task-1670b1f8). Step 4 used to append `ORG_DB_URL` and
`ORG_TEST_DB_URL` to the env file, and (W1.8) install the drop-ins. W1.9's rehearsal (task-a49a3f35, F2/F3)
moved the installing out of it: **step 4 now only refuses and changes nothing on the box.**

**Step 4 (refusals only):**

1. Refuse unless all three drop-ins exist in the checkout and all three units are installed.
2. Refuse unless `infisical_setup.py run Agents-Core prod --as contabo -- .venv/bin/python -c <connect>`
   connects with `ORG_DB_URL`. The snippet prints no value.

**Step 5 (guard, then stop, then import).** Only when `state/tasks.db` exists:

1. Refuse unless `select count(*) from tasks where status in ('pending','in_progress','queued_remote')` on
   `state/tasks.db` is 0 (a count that cannot be read is a refusal too). Nothing has changed yet.
2. `systemctl stop` `mooniex-watchdog`, `mooniex-secretary` and `mooniex-secretary-waker`. The rehearsal
   measured a 9 s window between the import and the archive; a row written in it would sit only in the
   archive and never reach the hub. The units are still on their OLD unit files here, because the drop-ins
   are not installed yet (F2). A `systemctl start` after a refused cutover therefore brings them back on
   sqlite, and `print_rollback` says so. Any failure after the stop (migrate, verify, archive, read-back)
   prints that rollback from an EXIT trap.
3. Migrate (`migrate_tasks_db.py`), then verify (`verify_migration_counts.py --mode subset`).

Steps 5, 5b and 7 (migrate, verify, read-back) take `ORG_DB_URL` through the same `infisical_run`,
not from a sourced file. Step 6 archives and tombstones `state/tasks.db`.

**Step 8 (switch, drop-ins, restart).** Runs after the migration and the tombstone, in this order:

1. Write `org_db: hub` into `/root/.config/mooniex/node.yaml` with `cutover_flip.set_org_db` (idempotent,
   every other line kept, a missing file created). The node file is written this late on purpose (CTO,
   iteration 2): it is the switch for the C-level and worker MCP servers, so a session spawned before
   the migration would open the hub before it holds any rows.
2. Copy the three drop-ins to `/etc/systemd/system/<unit>.service.d/org-db.conf`, then `systemctl
   daemon-reload`. Only now, right before the restarts (F2): a unit that systemd restarts earlier (the
   watchdog is `Restart=always`) would load the drop-in and start on a half-migrated hub.
3. Restart the three units and require all three active.

It fails if a write, the reload, a restart or an `is-active` check fails, and then prints the rollback,
which names removing the `org_db:` line and the drop-in directories. `ORG_TEST_DB_URL` is gone: nothing in
the cutover reads it, so W1.9's rehearsal fetches its own `org_test` URL. No env file is read or written.
The script exports `MOONIEX_NODE_YAML="$NODE_YAML"`: `cutover_flip.py` reads `MOONIEX_NODE_YAML` only (F4),
so the one path is used by the write, the rollback line it prints and any run pointed at a scratch file.

**Wrapper (`scripts/hub/with-org-db-env.sh`).** Contabo's env file holds `POSTGRES_*` only, so a wrapper
that only sourced it would leave the Contabo MCP servers on SQLite after the cutover. The order is now:
(a) source the env file if it exists (the Mac's carries `ORG_DB_URL`); (b) if `ORG_DB_URL` is still
unset and `/etc/infisical/<host>.env` exists (`<host>` from `ORG_HOST`, else the node file's `host:`;
`INFISICAL_CRED_DIR` and `MOONIEX_INFISICAL_ID_FILE` override the path for tests), exec
`tools/infisical_setup.py run Agents-Core prod -- "$@"`; (c) else a plain exec. The identity file is
tested for existence only, and the wrapper prints no value.

**Rollback** (both `contabo-cutover*.sh` headers): remove the three drop-ins and their now-empty
`<unit>.service.d` directories (`rmdir --ignore-fail-on-non-empty`, F7), remove the `org_db:` line
(`MOONIEX_NODE_YAML=<node.yaml> cutover_flip.py --rollback --apply`), `systemctl daemon-reload`, restart
the three units. A cutover that stopped after step 5 and before step 8 has no drop-ins to remove: after the
tasks.db half of the rollback, `systemctl start` the three units. Tests:
`tests/test_w18_contabo_consumers.py` and `tests/test_w19b_cutover_fixes.py`, against fakes and a throwaway
root. W1.9 rehearses both directions against `org_test`.

## Runbook lines for the W1.10 window (W1.9 F5, F6)

- **Order of the two legs.** Mac cutover first, or Contabo first: either order is safe. The rehearsal
  measured 0 key overlap between the Mac ledger and Contabo's (tasks 0, c_level_sessions 0; `events` ids
  overlap, which is what `--append-events` is for), and both legs are idempotent. The script's old comment
  that the hub "already holds the Mac's ~1108 tasks" is not a precondition.
- **Console shows a stale task list after the cutover.** `mooniex-console` (node) holds `state/tasks.db`
  open read-only. After the archive it keeps answering from the archived file with no error: the list is
  frozen at the cutover moment, stale but not lost. It stays that way until its `src/orgdb.js` hub reader
  ships (the read-only `org_ro` role, below) and Console is restarted once. Until then, expect stale
  Console tasks and do not read them as data loss.

**Open item, not in this task.** `deploy/systemd/org-snapshot.service` still has
`EnvironmentFile=/root/.config/mooniex/org-db.env`. That file has no `ORG_DB_URL`, so the snapshot export
would get none after the cutover. It needs its own drop-in (root, `infisical_setup.py run ... --as contabo`).

## Console (`mooniex-console:src/orgdb.js:14`)

A read-only Postgres role `org_ro` with `SELECT` only. Its password is generated on the box and
`put --stdin` into `MoonieX-Console/prod`. Console starts through `infisical run`. That is a
`mooniex-console` task for that project's owner.

## Gates

- Writing `ORG_DB_URL` into Infisical, and creating the `org_ro` role and password, are secret acts
  and need the CEO's approval. The Infisical lane owner (cto-885ae930) is told first.
- The secretary's owner is told before the unit is restarted under `infisical run` (CLAUDE.md §Secrets).
  The restart itself happens in the W1.10 window, where every service restarts anyway.
