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
- **C-level MCP servers on Contabo**: the W1.6 switch, `org_db: hub` in `/root/.config/mooniex/node.yaml`.
  The wrapper gets `ORG_DB_URL` from `infisical run` when the env file lacks it (see the installer section).

## The installer: `scripts/hub/contabo-cutover-remote.sh` step 4 (no new script)

The Contabo half of the cutover already exists and runs inside G1 (W1.10), so the installer is its
step 4, not a new script (task-1670b1f8). Step 4 used to append `ORG_DB_URL` and `ORG_TEST_DB_URL` to
the env file. It now does this, and refuses before any write if a check fails:

1. Refuse unless all three drop-ins exist in the checkout and all three units are installed.
2. Refuse unless `infisical_setup.py run Agents-Core prod --as contabo -- .venv/bin/python -c <connect>`
   connects with `ORG_DB_URL`. The snippet prints no value.
3. Copy the three drop-ins to `/etc/systemd/system/<unit>.service.d/org-db.conf`.
4. Write `org_db: hub` into `/root/.config/mooniex/node.yaml` with `cutover_flip.set_org_db`
   (idempotent, every other line kept, a missing file created).
5. `systemctl daemon-reload`. Nothing restarts yet.

Steps 5, 5b and 7 (migrate, verify, read-back) take `ORG_DB_URL` through the same `infisical_run`,
not from a sourced file. The three units restart in a new step 8, after the migration and the
tombstone, and the script fails if any is not active. `ORG_TEST_DB_URL` is gone: nothing in the
cutover reads it, so W1.9's rehearsal fetches its own `org_test` URL. No env file is read or written.

**Wrapper (`scripts/hub/with-org-db-env.sh`).** Contabo's env file holds `POSTGRES_*` only, so a wrapper
that only sourced it would leave the Contabo MCP servers on SQLite after the cutover. The order is now:
(a) source the env file if it exists (the Mac's carries `ORG_DB_URL`); (b) if `ORG_DB_URL` is still
unset and `/etc/infisical/<host>.env` exists (`<host>` from `ORG_HOST`, else the node file's `host:`;
`INFISICAL_CRED_DIR` and `MOONIEX_INFISICAL_ID_FILE` override the path for tests), exec
`tools/infisical_setup.py run Agents-Core prod -- "$@"`; (c) else a plain exec. The identity file is
tested for existence only, and the wrapper prints no value.

**Rollback** (both `contabo-cutover*.sh` headers): remove the three drop-ins, remove the `org_db:` line
(`cutover_flip.py --rollback --apply`), `systemctl daemon-reload`, restart the three units. Tests:
`tests/test_w18_contabo_consumers.py`, against fakes and a throwaway root. W1.9 rehearses both
directions against `org_test`.

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
