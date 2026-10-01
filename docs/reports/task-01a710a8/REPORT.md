# task-01a710a8: the join door, Org-Node, least privilege for the endpoint (W4.6c)

Developer worker, branch `agent/developer-task-01a710a8`, base 8a170d28. Claude only (IRON §59).
Nothing here touched live Infisical, GitHub, Contabo or winbox, and `door.sh` / `join.sh` were never
run for real: every test uses shims or a scratch Postgres on 127.0.0.1.

## What was built

**A. The door** (`deploy/join/door.sh`, POSIX sh, root on Contabo). `open [--minutes N]` (1 to 120,
default 30) schedules its own close first (`systemd-run --on-active=Nm --unit org-join-door-close`,
replacing an earlier timer), then starts `org-join.service`, then the proxy compose, then prints one
line `open until <UTC time>`; any failure shuts everything again and exits 1. `close` stops proxy and
service and cancels the timer, prints `closed`, idempotent. `status`. `approve --host H --fingerprint F`
runs `hq_join approve` and prints the result only. `open` copies itself to
`/var/lib/org-join-door/door.sh` (700) and schedules that copy, so the close still runs if the card
runner deletes its own copy; from a pipe it copies the checkout's file after checking its header
line. The unit is no longer enabled (no `[Install]`) and the proxy has `restart: "no"`. The README
has the exact `tools/ask_run.py create` forms (open, approve, close, status), each checked with
`--dry-run`; the approve card's `--why` carries the host name and the 8-character fingerprint.

**B. F2, Org-Node** (`tools/infisical_setup.py`). `NODE_PROJECT = "Org-Node"`, prod only; `plan` and
`apply` create it (and the `/org-join` folder in Agents-Core prod). `org-node` gets viewer on Org-Node
and nothing else: `ensure_node_identity` refuses, changing nothing, when it is a member of any other
project (and refuses a wider role on Org-Node); `apply` prints a `!` line for the stray membership.
`put` and `import-env` refuse any name but `CLAUDE_CODE_OAUTH_TOKEN` in Org-Node, and the code never
writes its value. `node_readable_secret_names` reads Org-Node; the documented set is now one line.
`join.sh`, `join.ps1`, `docs/ops/hq-join.md` and the README say `run Org-Node prod --as <host>`.

**C. F3, least privilege.** `deploy/join/org_join_role.sql` (idempotent, password from the psql
variable or the environment, never in the file, column grants derived from the SQL, two row-guard
triggers, a self-check of every privilege). `tools/join_api.py` reads `ORG_JOIN_DB_URL`; with only
`ORG_DB_URL` it exits 2 unless `JOIN_API_ALLOW_ORG_ROLE=1`, then it connects and logs one warning.
It hands its pooled connection back at the end of every request slot (the role allows 5). The unit
runs as the system user `org-join`, with only the `/org-join` folder injected, keeping every W4.6b
sandbox directive. Machine credential: the root leg reads `/etc/infisical/contabo.env` (still root
0600), runs `infisical_setup.py run ... --path /org-join`, and `setpriv` drops to `org-join`; no
permission under `/etc/infisical` changes and no STOP was needed. `deploy/join/org_join_role.py` is a
small helper that makes the role password in memory, runs the SQL with it through the environment and
prints the role's URL on stdout for `put --stdin` (argv, files and terminal never see it).

## Files

New: `deploy/join/door.sh`, `deploy/join/org_join_role.sql`, `deploy/join/org_join_role.py`,
`tests/test_w46c_door.py`, `tests/test_w46c_join_role.py`, `tests/test_w46c_node_project.py`,
this report.

Changed: `tools/infisical_setup.py`, `tools/hq_join.py`, `tools/join_api.py`,
`deploy/join/org-join.service`, `deploy/join/docker-compose.join-proxy.yml`, `deploy/join/join.sh`,
`deploy/join/join.ps1`, `deploy/join/README.md`, `docs/ops/hq-join.md`,
`scripts/test_infisical_setup.py`, `tests/test_w42_provision.py`, `tests/test_w43_join_api.py`,
`tests/test_w44c_join_followups.py`, `tests/test_w45_bind.py`, `tests/test_w46a_hub_fixes.py`,
`tests/test_w46b_node_fixes.py`.

## Test numbers

| Run | Result |
|---|---|
| Full suite, `python -m pytest -p no:warnings`, once, no `ORG_TEST_DB_URL` | 5849 passed, 356 skipped, 0 failed (9 min 18 s) |
| `scripts/test_org_tools_registry.py` | verdict line `ALL PASS` |
| `scripts/test_mcp_role_config.py` | verdict line `OK — 0 failure(s)` |
| `scripts/test_tool_parity.py` | verdict line `ALL PASS` |
| Join tests against a real scratch Postgres 16.15 (`ORG_TEST_DB_URL`), 10 files | 974 passed, 1 skipped, 0 failed |
| New files collected: `test_w46c_door.py` / `test_w46c_join_role.py` / `test_w46c_node_project.py` | 179 / 97 / 21 (the pg-only tests among them skip without `ORG_TEST_DB_URL`) |
| `shellcheck -s sh deploy/join/door.sh`, `sh -n` | clean; the tests also run it under `/bin/dash`, `/bin/sh`, `/bin/bash` 3.2 |

The pg-gated tests include a real accept and a real sealed fetch over HTTP, as `org_join`; a matrix of
statements `org_join` must be refused; the row guards; the 5-connection limit; a second run, a
rotated password, a short password and drift all handled by the file.

## The live steps, in order

Nothing below has been run. The full text, with the exact commands, is in `deploy/join/README.md`,
"Live order".

1. **Create Org-Node.** `infisical_setup.py plan`, then `apply` (identity `setup`, CEO's go): creates
   the project Org-Node (prod only) and the `/org-join` folder in Agents-Core prod.
2. **CEO puts `CLAUDE_CODE_OAUTH_TOKEN` in Org-Node prod** (gate G3). Until he does, `run Org-Node prod`
   refuses to start (empty folder), so a node's probe fails. Do this before step 3.
3. **Move the `org-node` membership.** Infisical UI: add `org-node` as Viewer on Org-Node first, then
   remove it from Agents-Core. Existing nodes then run `run Org-Node prod --as <host>`.
4. **Create the role `org_join` and `ORG_JOIN_DB_URL`.** The pipeline in the README runs
   `org_join_role.py` under `infisical_setup.py run Agents-Core prod --as <id>` and pipes its one
   stdout line into `put Agents-Core prod ORG_JOIN_DB_URL --path /org-join --stdin`. Needs `psql`
   and a connecting role with CREATEROLE.
5. **`useradd`.** `sudo useradd --system --no-create-home --shell /usr/sbin/nologin org-join`, then
   check it can read the checkout and run the venv's python.
6. **Install the unit, not enabled.** `cp deploy/join/org-join.service /etc/systemd/system/`,
   `systemctl daemon-reload`, never `enable`; stop the old always-on unit and proxy once.
7. **Try it** with an `open --minutes 5` card, the README's Checks, then a `close` card.

## Things the CTO should look at

- **`hq_join.accept` changed shape.** One `INSERT ... ON CONFLICT DO UPDATE ... excluded.*` is now
  `INSERT ... DO NOTHING` plus an `UPDATE ... WHERE host = ? AND status = 'left'`. Found by running
  the real accept as `org_join`: Postgres asks for SELECT on every column read through `excluded`,
  which would have forced SELECT on `pubkey` and `config_json`. Race analysis (READ COMMITTED) is in
  the code comment; the race and rejoin tests pass on SQLite and on Postgres.
- **`door.sh approve` runs under the full `org` role**, as `secretary`, not as `org_join`: the row
  guard forbids the endpoint's role to approve, on purpose. A second approval-only role is the
  alternative; not done, one more credential.
- **`restart: "no"` on the proxy** (was always-restart), so a reboot cannot reopen the route.
- **The old always-on proxy and unit**, if installed, must be stopped once (README step 6).
- **Paths I touched that a strict "touches" list may not name** (TASK.md carries none): `tools/hq_join.py`
  (the accept SQL, the documented set), `tests/test_w43_join_api.py` (2 lines: the pg-parametrised
  start test sets `JOIN_API_ALLOW_ORG_ROLE=1`), `docker-compose.join-proxy.yml`, `scripts/test_infisical_setup.py`,
  and the new `deploy/join/org_join_role.py` (not asked for: the task said the operator passes the
  password from Infisical, and this is how it gets there without touching argv or a file).
- **One flake seen once**: `tests/test_w43_join_api.py::test_logs_name_method_path_status_and_host_and_nothing_secret[sqlite]`
  failed in one combined run and passed alone and on every rerun, including the final full run.
  Not investigated further.
- **Open question about the Run Inbox runner:** I could not see how it places a fetched script
  (a temp file it deletes, or the checkout). `door.sh` does not care: it copies itself to a
  persistent path, or the checkout's copy when run from a pipe.
- A node that joined before Org-Node read Agents-Core with the old membership; `docs/ops/hq-join.md`
  has a new section for what to rotate when such a node leaves.

## Skill learning

- MISSING [CTO_Procedure_KeyFetch §generated secrets]: nothing says how to create a database role's
  password and store its URL in one step without it touching argv, a file or the terminal (make it in
  memory, hand it to psql through the environment, print the URL on stdout into `put --stdin`) ·
  evidence: task-01a710a8, `deploy/join/org_join_role.py`
- MISSING [ecc:postgres-patterns §privileges]: `INSERT ... ON CONFLICT DO UPDATE` with `excluded.col`
  needs SELECT on every column read through `excluded`, so column-level grants that look sufficient
  on paper fail at run time · evidence: task-01a710a8, aa0a47a6 (`tests/test_w46c_join_role.py`,
  real accept as `org_join`); only a test against a real Postgres found it
- COSTLY [no owner]: a mock-only suite cannot show privilege errors; setting up the scratch Postgres
  (`initdb` + `pg_ctl` under `/opt/homebrew/bin`, 127.0.0.1, trust auth) took minutes and found the
  one real bug of the task · prevented by: a documented one-liner for a throwaway local Postgres in
  the testing playbook
- MISSING [no owner]: the GateGuard Bash gate also fires on a command that only contains a
  file-writing script (`open(p,'w')` in a heredoc), not just on `rm`; stating the facts and retrying
  the identical call works · evidence: this session, the README edit script (n=1)
