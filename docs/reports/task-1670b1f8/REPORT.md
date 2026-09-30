# task-1670b1f8 — Org Mesh W1.8: Contabo ledger consumers reach the hub

Branch `agent/developer-task-1670b1f8`, base `0411789d`. Built and tested only. Nothing was installed on any
machine, nothing ssh'd, the real `/etc`, real `node.yaml` and the real env file were never touched, and
`/etc/infisical/contabo.env` was never opened (tests check existence only; no secret value is printed anywhere).

## Summary

Contabo's env file has no `ORG_DB_URL`, so the plan's "append to the env file" would break the Infisical rules and
would leave the Contabo MCP servers on SQLite after the cutover (split brain). Now `ORG_DB_URL` comes from Infisical
`Agents-Core/prod` through `infisical_setup.py run` everywhere: a wrapper fallback, three tracked systemd drop-ins,
and a reworked `contabo-cutover-remote.sh` step 4 (plus a new step 8 that restarts the units after the migration).

## Files Changed

- `scripts/hub/with-org-db-env.sh` — (a) source the env file if it exists; (b) if `ORG_DB_URL` is still unset and
  `<INFISICAL_CRED_DIR or /etc/infisical>/<host>.env` exists (host from `ORG_HOST`, else the node file's `host:` line,
  validated as `[a-z0-9_-]`), `exec python3 tools/infisical_setup.py run Agents-Core prod -- "$@"`; (c) else plain exec.
  Identity file tested with `[ -f ]` only. Prints nothing.
- `deploy/systemd/mooniex-watchdog.service.d/org-db.conf` — new. `ExecStart=` cleared then reset through
  `infisical_setup.py run Agents-Core prod --as contabo --` to the venv python `-m runners.watchdog --loop`.
- `deploy/systemd/mooniex-secretary.service.d/org-db.conf` — new. Same, with `ExecStart=+` (privileged fetch), then
  `setpriv --reuid=secretary --regid=secretary --init-groups --` drops to the service user; `Environment=HOME=/home/secretary`.
  The unit's `EnvironmentFile=` lines are not cleared.
- `deploy/systemd/mooniex-secretary-waker.service.d/org-db.conf` — new. Same as the secretary, running `-m runners.secretary_waker`.
  Each drop-in carries a comment with why, the design doc path and the rollback.
- `scripts/hub/contabo-cutover-remote.sh` — step 4 reworked: refuse (before any write) unless the three drop-ins exist
  in the checkout and the three units are installed, and unless `Agents-Core/prod ORG_DB_URL` connects to the hub;
  then copy the drop-ins, write `org_db: hub` to node.yaml via `cutover_flip.set_org_db`, `systemctl daemon-reload`.
  Steps 5, 5b and 7 take `ORG_DB_URL` through the new `infisical_run` helper. New step 8 restarts the three units
  after migration and tombstone, waits `RESTART_SETTLE_S` (default 3), and exits 1 if any unit is not `is-active`.
  The `ENVF` sourcing, the env-file append and `ORG_TEST_DB_URL` are gone. Header rollback text updated.
- `scripts/hub/contabo-cutover.sh` — header only: step 4/5/8 text and the full rollback (remove drop-ins,
  `cutover_flip.py --rollback --apply`, `daemon-reload`, restart).
- `tests/test_w18_contabo_consumers.py` — new, 64 tests: wrapper (env file / Infisical leg / plain exec, host parsing,
  hostile host names, no value printed), drop-ins (parse, no `EnvironmentFile=`, `+` and `setpriv` shape, and each
  ExecStart's arguments run through the real `tools.infisical_setup.main` parser), remote script step 4 and step 8
  against fake `python3`/`systemctl`/`tmux`, a throwaway git origin + work clone, and a fake venv (refuse path changes
  nothing; happy path installs three drop-ins, writes the node line, restarts last; unit not active fails).
- `tests/test_hub_cutover_scripts.py` — `_run_remote` no longer sets `ENVF`; the step-5 and step-5b pin tests now
  also call `_assert_runs_inside_infisical_run`. This file was in the touch list; no test outside it pinned old behaviour.
- `docs/design/org-mesh-w18-contabo-consumers.md` — installer section now names `contabo-cutover-remote.sh` step 4
  (no new script) and the wrapper change; env-file facts, the C-level MCP bullet and the rollback bullet updated;
  one open item added (`org-snapshot.service`, below).
- `docs/reports/task-1670b1f8/REPORT.md` — this file.

## Commits

- 68a6d737 — W1.8: with-org-db-env.sh falls back to infisical run when the env file has no ORG_DB_URL
- 3ee0ce64 — W1.8: systemd drop-ins for watchdog, secretary, secretary-waker
- f82d0df8 — W1.8: cutover step 4 installs drop-ins + node file switch, ORG_DB_URL via infisical run
- bfc55151 — W1.8: tests for the wrapper, the drop-ins and cutover step 4; design doc installer section
- 0c73d32a — W1.8: test that each drop-in ExecStart parses through the real infisical_setup.py main
- (report commit follows this file)

## Tests

- ran: `.venv/bin/python -m pytest` (full suite, from the worktree, default env, no `-q`) — `3606 passed, 27 skipped in 312.38s (0:05:12)`, exit=0
- ran: `ORG_HOST=contabo .venv/bin/python -m pytest` (full suite, same worktree) — `3606 passed, 27 skipped in 339.57s (0:05:39)`, exit=0
- ran: `.venv/bin/python scripts/test_mcp_role_config.py` (standalone) — 57 PASS lines, 0 FAIL, last line `OK — 0 failure(s)`, exit=0
- also: `pytest tests/test_w18_contabo_consumers.py tests/test_hub_cutover_scripts.py` — 100 passed, 1 warning
- `bash -n` ok on `scripts/hub/with-org-db-env.sh`, `scripts/hub/contabo-cutover-remote.sh`, `scripts/hub/contabo-cutover.sh`
- passed: 3606 (per full run)
- failed: 0
- skipped: 27

Mutation probe: the old wrapper and the old remote script run against the new tests gave 22 failed, 39 passed, so
the tests can fail. Scripts restored afterwards and re-checked with `bash -n`.

## Issues / Blockers

- none blocking. No test outside the touch list pinned old behaviour, so nothing needed a `dev_message`.
- **`ORG_TEST_DB_URL`: DROPPED.** Nothing in the cutover reads it; only tests read it from env. W1.9's rehearsal must fetch
  its own `org_test` URL. Step 4 no longer produces it.
- **Untested on a real systemd.** The drop-in syntax (`ExecStart=+`, `setpriv --reuid/--regid/--init-groups --`) was
  only parsed and checked against `infisical_setup.main`'s argument split; no ssh and no `systemd-analyze` on this Mac.
  W1.9's rehearsal on the box is where it is proven. `setpriv` availability on Contabo is assumed (util-linux).
- `deploy/systemd/org-snapshot.service` still uses `EnvironmentFile=/root/.config/mooniex/org-db.env`. That file has no
  `ORG_DB_URL`, so the snapshot export gets none after the cutover. Outside the touch list, not fixed; it needs its own
  drop-in (root, `infisical_run ... --as contabo`). Recorded as an open item in the design doc.

## Notes for Reviewer

- **Ordering of the node.yaml write.** `org_db: hub` is written in step 4, before migration and tombstone (as briefed).
  A worker spawned between step 4 and step 8 would get hub MCP config while the watchdog is still on SQLite. C-level
  sessions are closed by step 1, so this window is small. Consider moving the write to just before step 8.
- **Step 4 has one preflight not in the brief:** it refuses if a unit is not installed (`systemctl cat`). The watchdog
  unit must be installed (W0.5) before G1, or the cutover refuses at step 4 with nothing changed.
- **Wrapper identity-file test uses `[ -f ]`.** `/etc/infisical/<host>.env` is root 0600 and the directory may be
  unreadable to a non-root process; then the wrapper would fall to plain exec (SQLite). Fine for root workers on
  Contabo, not verified on the box.
- **Wrapper does not pass `--as`.** It relies on `infisical_setup.self_host()` (contabo on Linux). It also honours
  `INFISICAL_CRED_DIR` and `MOONIEX_INFISICAL_ID_FILE`; the second is a test hook.
- **Secretary owner must be told before the restart** (design doc Gates, CLAUDE.md §Secrets). The restart happens in step 8 of the W1.10 window.
- **The secretary interpreter changes** from `/usr/bin/python3` to the venv python (system python has no `psycopg`); measured facts are in the design doc.
- **"Dry path" reading:** I took it as the refuse path (connect check fails, nothing changed: no drop-ins, no node.yaml write,
  no daemon-reload/restart) plus a full fake-driven happy path. There is no real `--dry-run` flag.
- Suite time is 5+ minutes per run; both runs used the same worktree.

## Skill learning

- MISSING [no owner | hooks] : the `self_repo_guard` hook treats the text `<host>.env` inside a `git commit -m` message as a redirect into `.env` and blocks the commit. Reword to avoid it; the guard was not bypassed. · evidence: task-1670b1f8, first commit attempt (Bash blocked, reworded, then committed)
- COSTLY [no owner | hooks] : GateGuard arms once per new or edited file (Edit/Write) plus once per Bash session; with 9 touched files that was about a dozen blocked-then-retried calls. The facts must be stated and the identical call retried; stating them first does not pre-empt it. · evidence: task-1670b1f8 session · prevented by: batch all edits per file into one Edit where possible, and budget one error per file
