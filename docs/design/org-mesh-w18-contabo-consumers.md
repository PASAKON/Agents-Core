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
| Which key names `/root/.config/mooniex/org-db.env` holds | **not checked** (the file is not opened) |

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
- The existing file stays, as the rollback, for 7 green days (the line-queue rule), then goes.

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
  The W1.6 wrapper still sources the existing env file. Moving it to `infisical run` is a follow-up,
  and it waits for the secretary's own phase-3 move.

## The installer: `scripts/hub/cutover-contabo.sh` (dry-run by default)

`--apply` copies the three drop-ins, writes `org_db: hub` (through `cutover_flip.set_org_db`), runs
`daemon-reload` and restarts the three units. `--rollback --apply` removes all four and restarts.
Dry-run prints the diff. W1.9 rehearses both directions against `org_test`.

## Console (`mooniex-console:src/orgdb.js:14`)

A read-only Postgres role `org_ro` with `SELECT` only. Its password is generated on the box and
`put --stdin` into `MoonieX-Console/prod`. Console starts through `infisical run`. That is a
`mooniex-console` task for that project's owner.

## Gates

- Writing `ORG_DB_URL` into Infisical, and creating the `org_ro` role and password, are secret acts
  and need the CEO's approval. The Infisical lane owner (cto-885ae930) is told first.
- The secretary's owner is told before the unit is restarted under `infisical run` (CLAUDE.md §Secrets).
  The restart itself happens in the W1.10 window, where every service restarts anyway.
