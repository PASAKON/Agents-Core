# Join drill (Org Mesh W4.7)

`scripts/drill-join.sh` joins one throwaway node to the mesh, gets it approved and provisioned,
hands it a probe task, makes it leave, and then checks that nothing of it is left. It is the only
thing behind the **L8** cell of `tools/mesh_check.py`, and L8 green on every `--expect w5 --live`
run is part of the charter's done line.

It runs **on Contabo, as root, from a checkout of `origin/main` (a detached worktree under
`/opt/MoonieXHQ/Agents/Core/worktrees/`, see below), as one Run Inbox card**. The CEO
taps once. Nothing is typed, no login is done on the node. Run it only when a CTO has decided to:
it opens the public join door (30-minute cap, closed as soon as the node is provisioned) and
creates and revokes real credentials.

## What the CEO's tap means

The tap on the card is the human approval of the throwaway node. Normally `hq_join approve` needs a
person to compare the fingerprint on the node's own screen with the one the hub shows. Here the
script reads the fingerprint from the node's output (fallback: `age-keygen -y <identity> | tail -c 9`
on the node) and passes it to `approve` itself. It never takes the fingerprint from `hq_join status`:
that is the hub's copy, and approving it would prove nothing. So the drill proves the approval
**gate** works (a wrong fingerprint is refused, a right one opens `provision`), not that a person
compared two screens.

## The Run card

Push the commit first; the card runs a script at a pushed SHA.

```bash
python3 tools/ask_run.py create --host contabo \
    --script Agents-Core@<pushed-sha>:scripts/drill-join.sh \
    --cwd <worktree path given by the Contabo CTO> --timeout 7200 --risk amber \
    --why "W4.7 join drill: a throwaway container joins the mesh as drill-<utc stamp>. Your tap IS the human approval of that node. It opens the join door for the run, then creates and revokes one tailnet device and one GitHub deploy key, has the hub hand the node the Claude token through the token service (the token is never written on the node) and then makes the hub refuse the node, and pushes one probe branch that it deletes. Needs the token service running (deploy/node-token/README.md), a join DSN that logs in, 1.5 GB free RAM, about 20 minutes. Do not cancel it or restart the Console while it runs: a killed card leaves the node joined (recovery: docs/ops/join-drill.md, If the card was killed)." \
    --expected "result: PASS, every step ok, a re-os-drills row printed, the door closed, no drill-* container or volume left"
```

Add `-- --log-to-repo` after the script to also append the `re-os-drills` row to the repo file (see
below). Do a free look first with `--dry-run` (it prints every step, touches nothing):

```bash
python3 tools/ask_run.py create --host contabo --script Agents-Core@<sha>:scripts/drill-join.sh \
    --cwd <worktree path given by the Contabo CTO> --timeout 60 --risk green \
    --why "W4.7 join drill, dry run: prints the plan, touches nothing" \
    --expected "one line per step, exit 0" -- --dry-run
```

Exit codes: **0** pass; **1** the drill ran and failed (the JSON names the step); **2** refused at
preflight, nothing started and nothing written (a stale join DSN and a token service that is down or
not loaded are two of the refusals). An Infisical leg that cannot load its folder stops
before preflight with `infisical_setup.py`'s own message (non-zero, no JSON, nothing started).

## Which code runs

The live checkout on Contabo can be far behind `origin/main` (106 ahead and 27 behind on 2026-10-03),
so it cannot carry this drill. The Contabo CTO makes a detached worktree of `origin/main` under
`/opt/MoonieXHQ/Agents/Core/worktrees/<name>` and puts its path in the card (`--cwd`). Two sets of
code take part, and they are **not the same checkout**:

| Part | Runs the code of | Why |
|---|---|---|
| The drill script and every `python -m tools.*` call it makes (`hq_join` mint, approve, provision, leave, status, `mesh_check --join-drill`) | the checkout the card runs in: `CORE` = `git rev-parse --show-toplevel` of the working directory, else `/opt/MoonieXHQ/Agents/Core`. The script changes into `CORE`, so `python -m` loads the tools from there | that is the code under test |
| Python itself | `CORE/.venv/bin/python3` when it exists, else `/opt/MoonieXHQ/Agents/Core/.venv/bin/python3` | a fresh worktree has no `.venv` |
| The join API (`join.sh`, the token and fingerprint checks) and `door.sh`'s own approve leg | the **live** checkout, `/opt/MoonieXHQ/Agents/Core`, because `deploy/join/org-join.service` hardcodes that path | the service is not started from the worktree |

So a pass proves the worktree's tools against the live checkout's join service. Preflight prints both
commits and the run records them in the JSON (`code.drill`, `code.join_service`); a note says so when
they differ. `unknown` means git could not name the commit.

**Before the card**, the Contabo CTO checks that the join-path files of the live checkout match
`origin/main`, because those are the files the join service really runs:

```bash
git -C /opt/MoonieXHQ/Agents/Core diff --stat origin/main -- \
    tools/join_api.py tools/hq_join.py lib/db.py lib/tailscale_api.py deploy/join/
```

Empty output means the live join service is on the code under test. Any file listed means the drill
would test the new tools against an old service: update the live checkout first, or accept that the
result says so (`code.join_service` shows which commit it was).

Preflight also refuses (exit 2) when `CORE/tools/mesh_check.py` has no `--join-drill` or
`CORE/tools/join_api.py` has no `--check-db`: that is a checkout from before this drill, or not an
Agents-Core checkout at all.

The drill also needs two things from the hub side, and refuses (exit 2) before the door opens when
either is missing: the join role's DSN (`ORG_JOIN_DB_URL`, Agents-Core prod `/org-join`) must log in,
and the **token service** (`deploy/node-token/README.md`, unit `org-node-token`) must answer
`/health` with `token_loaded` and `db` both true. The drill finds the service at
`DRILL_TOKEN_URL`, else `ORG_NODE_TOKEN_URL`, else `http://<tailscale ip -4>:792/v1/token`; the same
URL goes into the node's bundle at `provision`.

## What one run does

| step | what happens | a red here means |
|---|---|---|
| `preflight` | the script is a readable file (it re-runs itself through Infisical, `/org-join` and then the hub wrapper, so a pipe is refused); this checkout's `tools/mesh_check.py` has `--join-drill` and `tools/join_api.py` has `--check-db` (the card runs the script at a pushed sha, the tools come from the checkout: a stale checkout is refused here, not after the join); root; `free -m` available >= 1500 MB; docker, curl, gh, git, perl; join door `closed`; no `drill-*` container, volume or non-`left` host; `TAILSCALE_OAUTH_CLIENT_ID/_SECRET` and `ORG_JOIN_DB_URL` in the environment; **`ORG_JOIN_DB_URL` logs in and answers `SELECT 1`** (`python -m tools.join_api --check-db`: the join API's own DSN choice and start-up read; gap 7); **the token service answers `/health` with `token_loaded` and `db` true**; the Tailscale and `gh` readers answer | exit 2, nothing started. The message says which. A stale DSN says "rotate with deploy/join/org_join_role.py", and the DSN is never printed. Memory: Contabo runs one heavy job at a time, run again when it is quiet |
| `door_open` | `deploy/join/door.sh open --minutes 30`. A trap closes it on every exit path, and the door is also closed as soon as `provision` ends | the door service would not start; check `door.sh status` |
| `container` | `ubuntu:24.04`, hostname `drill-<stamp>`, 1200 MB cap, `tailscaled --tun=userspace-networking`, state in a removable volume | docker problem (disk, image pull); nothing joined |
| `mint` | `hq_join mint --host drill-<stamp>`; the token is held in one shell variable | hub unreachable or `ORG_DB_URL` missing; see `docs/ops/hq-join.md` |
| `join` | in the container, `curl -fsSL <hub>/org-join/join.sh -o /tmp/join.sh`, then `sh /tmp/join.sh --host ...` with the token in the **environment** (never argv). Waits for the fingerprint line | join.sh stopped before accept. The detail carries its last log line (masked). Door closed? token expired (20 min)? hub URL wrong? |
| `approve` | `hq_join approve --fingerprint <read from the node>` | fingerprint mismatch: the node's key file and the hub's row disagree |
| `provision` | `ORG_W42_PROVISION=1` and `ORG_NODE_TOKEN_URL=<token URL>` set for this one command only. It makes **no Infisical call**: it seals `{host, token URL}` to the node's key. Then waits up to 15 min for join.sh to finish (it polls `/sealed`) | `provision` refused: no or bad token URL, or the Tailscale API refused. join.sh stopped: read its last line |
| `node_probe` | join.sh's own step 9 (`node_dispatch.py probe`, run under `tools/node_token.py` as the user, not root) must have passed | exit 2 from join.sh: joined but could not probe. Finding `node_probe_failed`. The node has no `ORG_DB_URL` so this may fail by design; it is reported, the run goes on. Exit 3 from `node_token.py` means the hub refused the node (not approved or left); exit 4, the node could not reach the token service |
| `token_worker` | on the node: `python3 -I tools/node_token.py run -- ... claude -p` must answer a nonce. The hub hands the token over (it is sealed to the node's key and opened in memory; nothing is written under `/etc/infisical` or anywhere on the node) and `claude` gets **only** `CLAUDE_CODE_OAUTH_TOKEN`. Everything else is stripped, and the token never appears on a command line: a `python3 -I -c` one-liner builds the clean environment (PATH, HOME, the token) and `exec`s `claude`, so it reaches the process by environment only | the W4.0 pass criterion failed: the hub refused (exit 3), could not be reached from the container (exit 4: the container reaches the hub's tailnet address over the docker bridge, a local address of the host), the answer could not be opened (exit 5), the token is missing from Org-Node prod (`/health` says so at preflight), wrong scope, or `claude` is not installed |
| `probe` | a task for the node is created `pending` (so no poller adopts it); the node commits `docs/ops/mesh-probe/contabo-<host>.md` with a `mesh-probe:` message on `agent/probe-<task>` and pushes; the hub `git ls-remote`s the same sha; <= 15 min. **Never merged.** | finding `deploy_key_read_only` (see gaps), or the node could not reach origin, or the sha on origin differs |
| `leave` | `ORG_W42_PROVISION=1 hq_join leave --host ... --live`. The flag matters: without it `w42_enabled()` is false, every revoker answers "not wired yet: live revocation is off" and nothing is removed | the three real steps (`status_leaving`, `tailscale_device`, `github_deploy_key`) must be `[ok]`. `status_leaving` is the hub's own write and runs first, with or without the flag: from then on the token service refuses the host. Each `authorized_keys` step answers `[ok] ... none placed` for a drill node (W4.1b, #214): nothing writes a joined node's key into any `authorized_keys` until W2.8 for nodes. A `not wired yet` failure (a hub on code older than #214) is still accepted and recorded as finding `leave_partial_authorized_keys_unwired`. A node that was never accepted has nothing to revoke, and the step is ok |
| `verify_tailnet` | Tailscale API: no device named `drill-<stamp>` | `leave` said ok but the device is still there |
| `verify_deploy_key` | `gh api repos/PASAKON/Agents-Core/keys`: no key titled `org-node:drill-<stamp>` | same, for the deploy key |
| `verify_token_refused` | `GET <token URL>?host=drill-<stamp>`: the hub answers **403 `left`**. Only the HTTP status and the `error` word are read; a 200 body (the sealed token) is never printed or stored. A node the drill never accepted has no `left` to show, and any 403 is its pass (`unknown_host`, or `not_approved` for a row that registered). A 200 or no answer at all is a red | the hub still hands the node a token after `leave` (R4 broken), or the token service did not answer, so a refusal cannot be shown |
| `verify_host_row` | `hq_join status --host`: row is `left`, or no row when the node was never accepted | `leave()` writes `left` only when every step is ok (gap 1, closed by W4.1b) |
| `verify_authorized_keys` | no line naming the host in contabo's `authorized_keys`, nor on winbox (`ssh $DRILL_WINBOX_SSH`, default alias `winbox`, reads `administrators_authorized_keys`). `findstr` exits 1 both for "no match" and for a file it cannot open, so the file is first proved readable with a search that must match (`/C:ssh-`, exit 0); only then is the host searched. Mac is skipped with a note until G2 (Remote Login is closed) | a line exists, or winbox could not be read. An unreadable winbox is a red, never a silent skip |
| `cleanup` | deletes the probe branch on origin, cancels the probe task, removes the container and volume, closes the door, then writes the JSON, the `events` row and prints the `re-os-drills` row | something is still there; the detail names what (`origin-branch:`, `task:`, `container:`, `volume:`, `door:`) |
| `record` | writes the `join_drill` events row (added after `cleanup`) | the hub could not be written; the file is still there, the Mac cannot see it |

A failed step does not stop the run: `leave`, every `verify_*`, and `cleanup` still run, and
`join-drill.json` gets `"ok": false` and `"failed_step"` set to the first step that is not ok. A
signal (SIGTERM, SIGINT, SIGHUP) takes the same path. SIGKILL does not, and the Run Inbox kills a
card with SIGKILL: see [If the card was killed](#if-the-card-was-killed).

## Reading the result

The run prints one line per step (`drill: <step>: ok (...)` or `FAILED (...)`), the result line, and
the `re-os-drills` row. The same data is in `state/mesh-check/join-drill.json` (gitignored) **of the
checkout the card ran in**: from a worktree that is the worktree's `state/`, not the live checkout's:

```json
{"ok": false, "at": "2026-10-03T14:00:00Z", "host": "drill-20261003-140000", "stamp": "20261003-140000",
 "steps": [{"name": "join", "ok": true, "detail": "node accepted; fingerprint abcd1234 read from the node's own output"},
           {"name": "probe", "ok": false, "detail": "the node's push was refused: its deploy key is read-only ..."}],
 "failed_step": "probe",
 "w40": {"remote_control": null, "remote_control_cmd": "claude remote-control", "remote_control_error": "", "remote_control_output": ""},
 "probe": {"task": "task-0123abcd", "branch": "agent/probe-task-0123abcd", "sha": "<40 hex>", "seconds": 42},
 "findings": ["deploy_key_read_only"], "notes": [], "minutes": {"to_joined": 3, "to_probe": null, "total": 9},
 "code": {"drill": "ab12cd3", "join_service": "ef45678"},
 "by": "scripts/drill-join.sh", "version": 1}
```

- `code` is which commit each part ran (see "Which code runs"): `drill` = the checkout the script and
  its tools ran from, `join_service` = the live checkout the join API and `door.sh` approve ran from.
- `steps` is what L8 reads (`name`, `ok`; `detail` is for people). L8 is green only if `ok` is true,
  `at` is under 7 days old, and every step is ok.
- `detail` is one printable-ASCII line, 200 characters at most, with token shapes masked.
- `findings` are named conditions found while running; `notes` are facts worth a line.
- `probe.sha` is the commit the node pushed. The branch is deleted at cleanup; the sha stays here.
- `w40` answers the W4.0 question, outside `steps`: does `claude remote-control` start on the OAuth
  token alone? `true` = the process was **still running** when `timeout` cut it at 25 s. That is
  all it says: it does not prove a session was opened, so read `remote_control_output`. `false` =
  it exited early (first line in `remote_control_error`); `null` = not reached.
  `remote_control_output` is the first line the command printed, kept in every case (URLs masked
  as `[url]`, ASCII, 200 characters at most). **It never fails the drill.**

### Seeing it from the Mac

`join_drill` is also written to the hub as an `events` row (kind `join_drill`, the same JSON). With
no local file, `check_l8` reads the newest such row, so `mesh_check --expect w5` on the Mac shows
the cell without a copy of the file (this is also how the live checkout sees a drill that ran in a worktree).
The file wins when both exist. A hub that cannot be read gives
`not run (... hub read failed ...)`, never green.

### `--log-to-repo`

By default the `re-os-drills` row is **printed only**: `state/re-os-drills.jsonl` is a repo file and
appending is a repo change. With `--log-to-repo` the script appends that one line, in the file's
existing shape (`date, machine, kind: "join-drill", scope, result, minutes_to_remote_access,
minutes_to_org_restore, bytes_from_git_mb, bytes_from_drive_mb, irreplaceable_lost_gb, human_steps,
gaps_found, by, ref`). It does not commit; a CTO does. From a worktree the line lands in that worktree's
`state/re-os-drills.jsonl`: commit it from there.

## If the card was killed

The Run Inbox stops a card with SIGKILL to its whole process group: on its timeout, on Cancel, and
when the Console restarts. SIGKILL cannot be trapped, so neither `leave` nor `cleanup` runs and no
JSON is written. Depending on how far the run got, these stay behind:

| Left behind | Made by step | Removed by |
|---|---|---|
| the open join door | `door_open` | `door.sh close` (it also closes itself after 30 minutes) |
| container `drill-<stamp>`, volume `drill-<stamp>-ts` | `container` | `docker rm -f -v`, `docker volume rm` |
| hosts row `drill-<stamp>`, its tailnet device and GitHub deploy key (the hub keeps serving the node its token until `leave` marks the row `leaving`) | `join` to `provision` | `hq_join leave --live` |
| the probe task (`pending`) and branch `agent/probe-task-<8 hex>` on origin | `probe` | `mesh_check --join-drill task-close`, `git push origin --delete` |

The next drill's preflight refuses while any of these exists; it does not remove them.

**Find the stamp.** The card output's first line is `drill: drill for drill-<stamp>; ...`. No such
line means preflight refused and nothing was made. Without the output, a leftover names it.

Run everything below as root on Contabo, in the checkout the card ran in (its `--cwd`):

```bash
PY=.venv/bin/python3; [ -x "$PY" ] || PY=/opt/MoonieXHQ/Agents/Core/.venv/bin/python3
docker ps -a --filter name=drill- --format '{{.Names}}'
docker volume ls -q --filter name=drill-
scripts/hub/with-org-db-env.sh "$PY" -m tools.hq_join status | awk '$1 ~ /^drill-/'
```

**Recover** in this order: close the door, stop the node, revoke its credentials, then tidy.

```bash
H=drill-<stamp>
bash deploy/join/door.sh close                          # prints "closed"
docker rm -f -v "$H"; docker volume rm "$H-ts"
python3 tools/infisical_setup.py run Agents-Core prod --path /org-join -- scripts/hub/with-org-db-env.sh env ORG_W42_PROVISION=1 "$PY" -m tools.hq_join leave --host "$H" --live
```

`leave` needs two Infisical folders: `/org-join` holds the Tailscale OAuth client, and the hub wrapper
loads only the root folder (`ORG_DB_URL`). Without the first leg, `leave` cannot delete the tailnet
device.

`leave` prints one line per step. `[ok] status_leaving`, `[ok] tailscale_device` and
`[ok] github_deploy_key` must all hold. Each `authorized_keys` line reads
`[ok] ... none placed` (W4.1b, #214), so the row becomes `left`. `leave` is safe to repeat: a
credential that is already gone counts as ok.

If the run reached `probe`, close its task and delete its branch:

```bash
scripts/hub/with-org-db-env.sh "$PY" -c "from lib import db; print(*[t['id'] for t in db.list_tasks(status='pending', project='mooniex-agents', limit=1000) if t.get('host') == '$H'])"
T=task-<8 hex>                                          # the id printed above
scripts/hub/with-org-db-env.sh "$PY" -m tools.mesh_check --join-drill task-close "$T"
git ls-remote origin "refs/heads/agent/probe-$T"        # prints a line only if the branch exists
git push origin --delete "agent/probe-$T"
```

**Check:**

```bash
bash deploy/join/door.sh status                         # closed
docker ps -a --filter name=drill- --format '{{.Names}}'; docker volume ls -q --filter name=drill-   # no output
scripts/hub/with-org-db-env.sh "$PY" -m tools.hq_join status | awk -v h="$H" '$1 == h'   # left
```

## What it proves, and what it does not

Proves, for one throwaway node on one box:

- join.sh, the token, accept, the fingerprint gate, `provision` and the sealed hand-over work end to
  end with a clean machine and no login;
- a node, handed the Org-Node OAuth token by the hub and holding it in memory only, can run
  `claude -p` (W4.0 criterion), and after `leave` the same hub refuses to hand that node the token
  again (CEO ruling 2026-10-03, R4);
- a task targeted at the node can be completed by the node and its commit reaches origin, in time;
- `hq leave --live` removes the tailnet device and the deploy key, and the script checks each of
  them directly (Tailscale API, `gh api`) and asks the token service for the host again (it must
  answer 403), not from `leave`'s own report.

Does **not** prove:

- that the **hub can dispatch to a joined node**. A joined node has no `mesh_ssh` route yet, so the
  probe's transport is `docker exec`. Hub-to-node dispatch is not exercised;
- a person comparing the fingerprint on two screens (see above);
- a real second machine: the node is a container on Contabo, tailnet in userspace mode;
- that `authorized_keys` cleanup works: nothing writes those keys until W2.8, so "none was ever
  there" is true but weak. Mac is not checked until G2;
- that the node's own `ORG_DB_URL` path works (the node has none);
- that the token service is reachable from a **real** second machine. The container reaches the hub's
  tailnet address (`http://100.x:792`) over the docker bridge, because that address is local to the
  host; its userspace `tailscaled` cannot route to 100.x, and `node_token.py` uses no proxy. This was
  not tried live. If the host firewall drops it, `token_worker` fails with exit 4 and the drill's
  detail names the exit code; fix the route, not the drill;
- that the token is not on the node's disk. The drill reads no files in the container for it; R3 is
  held by `node_token.py` (no file written, tested offline in `tests/test_w42b_node_token.py`).

## Known gaps in the pipeline that a run will hit

These come from reading `tools/hq_join.py` and `deploy/join/join.sh`, offline. A live run settles
each; the script reports them rather than hiding them.

1. **Closed by W4.1b (#214, 6ad7fc21).** `leave()` adds one `authorized_keys` step per other
   non-left host, and `left` is written only when no step failed. Each step used to fail with
   `not wired yet`, so the row could never become `left`. Now a step reports `none placed` (ok) for a
   joined node, because nothing writes a joined node's key into any `authorized_keys`. A core host
   (mac, contabo, winbox) still refuses: its W2.8a dispatch lines are placed and nothing removes them
   yet. W2.8 for nodes must record what it places, in the same change that places it.
2. **The deploy key is read-only** (`add_deploy_key` registers `read_only=True`), so the node cannot
   push its probe branch: step `probe` fails with finding `deploy_key_read_only`. Options: a
   write-capable deploy key for drill hosts only (CEO call: the repo is public, a write key on a
   throwaway container is a real credential), or another way to return the node's work. Until then
   the "probe commit on origin" criterion cannot pass.
3. **Closed by W4.2b.** `provision` used to need `/etc/infisical/setup.env` (an Infisical admin
   identity, which Contabo does not hold) and made one client secret per node. It now makes no
   Infisical call at all. `TAILSCALE_OAUTH_*` and `ORG_JOIN_DB_URL` come from Agents-Core prod
   `/org-join`, which the script loads itself when the caller has not (the first live card,
   RUN-20261003-0029-5164, refused at preflight because only the root folder was loaded). The box also
   needs a `gh` login that can read deploy keys.
4. **Winbox.** Reading `administrators_authorized_keys` needs an admin-capable ssh alias. Set
   `DRILL_WINBOX_SSH`; without one, `verify_authorized_keys` is red (unverifiable).
5. **join.sh step 9** (`node_probe`) reads the hub; the node has no `ORG_DB_URL`. May be red by
   design: finding `node_probe_failed`.
6. **Closed by #218 (5960ef33), proven live by run 5.** The hub refused every real deploy key (found by run 3). `DEPLOY_PUBKEY_RE` in
   `tools/hq_join.py` allowed 43 base64 characters after the fixed `AAAAC3NzaC1lZDI1NTE5AAAA`
   prefix. A real ssh-ed25519 key blob is 51 bytes, which is 68 characters: the prefix and 44 more.
   The test fixtures built keys with the same wrong length, so the tests passed. Fix: task-7dcc3d45
   (a decoded check, plus fixtures made with `ssh-keygen`). The join API runs from the live checkout
   (`LIVE_CORE`), so the fix must be on that checkout before the next run, not only on origin.
7. **A stale `ORG_JOIN_DB_URL` failed as an HTTP 500 at `join`** (found by run 4). Nothing checked that
   the DSN stored in Infisical `/org-join` could still log in. The door opened, and the first `/accept`
   died inside the join API. The fix is in W4.2b: preflight connects with the DSN (`SELECT 1`, plus a
   read of the three tables the join API reads at start-up) and refuses with "rotate with
   deploy/join/org_join_role.py" before the door opens. The check is `python -m tools.join_api
   --check-db`. It goes through `lib/db_pg.connect`, not `lib/db.get_conn`: `get_conn` falls back to a
   read-only snapshot with a warning when the hub refuses the login, so a check through it can never
   fail.
8. **Infisical Free cannot hold `org-node`** (found by run 5). Free allows 5 identities, and the CEO's
   user account counts as one. With contabo, mac, winbox and setup, the org is full, and
   `POST /api/v1/identities` answers 400. `IDENTITY_CAP` counted machine identities only, so it never
   refused first. CEO ruling 2026-10-03: no node identity; the hub serves the node its token (W4.2b,
   `deploy/node-token/`). `IDENTITY_CAP` now counts users too.

## Runs so far

| run | card | result |
|---|---|---|
| 1 | RUN-20261003-0029-5164 | refused at `preflight`: only the root Infisical folder was loaded, so there was no `TAILSCALE_OAUTH_*` (gap 3). The script now loads `/org-join` itself (#213) |
| 2 | (expired) | the card expired before it was tapped; nothing ran |
| 3 | RUN-20261003-0134-1883 | failed at `join` in 81 s: `the hub refused the request: deploy-pubkey is not an ssh-ed25519 public key line` (gap 6). `leave`, the five `verify_*` steps and `cleanup` were ok; the door closed and nothing was left behind |
| 4 | RUN-20261003-1420-fe8f | failed at `join` in 82 s: the join API answered HTTP 500 because role `org_join` could not log in to the hub; the DSN stored in Infisical `/org-join` was stale (gap 7). The first card for this run, RUN-20261003-0246-aac4, expired untapped. The DSN was rotated with `org_join_role.py` (card RUN-20261003-1424-d1f6). `leave`, the `verify_*` steps and `cleanup` were ok; the door closed |
| 5 | RUN-20261003-1425-1343 | failed at `provision` in 89 s: `POST /api/v1/identities -> HTTP 400`, Infisical Free's identity limit, so `org-node` could not be created (gap 8). Proven live for the first time: `join` with a real deploy key (gap 6 fix), `approve`, `leave`, and `verify_host_row` ("hosts row is left", gap 1). The door closed and nothing was left behind |

## W4.0 questions this drill answers live

| question | where the answer lands |
|---|---|
| Does `claude -p` work on a node with only `CLAUDE_CODE_OAUTH_TOKEN`, handed over by the hub from Org-Node prod? | step `token_worker` |
| Does `claude remote-control` start on that token alone? | `w40.remote_control`, `w40.remote_control_error`, and `w40.remote_control_output` (read this: `true` only means it was still running at 25 s) |

## Safety

- No secret is printed, written to the JSON, or put in a command line. The join token lives in one
  shell variable and reaches the container through the environment. The node's OAuth token never
  reaches the drill script at all: `node_token.py` on the node gets it sealed from the hub, and it
  reaches `claude` by environment only (a `python3 -I -c` exec builds the clean env; no
  `env VAR=...`, no `sh -c '... VAR="$VAR"'`), because container processes show in the host's `/proc`
  and in any execve audit. The drill reads only the HTTP status and the `error` word of the token
  service's answer, never a body. There is no `set -x`. Every
  detail passes a mask for `tskey-`, `sk-ant-`, `AGE-SECRET-KEY-`, `ghp_`-style tokens, and the join
  DSN is never printed (`--check-db` names the exception class only).
- No `.env` is created. The script re-execs itself through `tools/infisical_setup.py run Agents-Core
  prod --path /org-join` (the Tailscale OAuth client and `ORG_JOIN_DB_URL`; skipped when the caller
  already set them), then through `scripts/hub/with-org-db-env.sh` (the hub URL), like every Contabo
  consumer of the hub. That is the only Infisical call in the script; the node-side steps and
  `provision` make none.
- It deletes only names it made: `drill-<stamp>` container and volume, the `agent/probe-task-<hex>`
  branch (the name is checked before `push --delete`), and it only cancels its own probe task.
- The probe branch is never merged: the repo is public, and nothing from a throwaway node should
  reach `main`.

## Overrides (tests and odd boxes)

`DRILL_CORE` (default: the git top level of the working directory, else the live checkout),
`DRILL_LIVE_CORE` (the join service's checkout, default `/opt/MoonieXHQ/Agents/Core`; its `.venv` is the
fallback python), `DRILL_STATE_DIR`, `DRILL_ROWS_FILE`, `DRILL_PY`, `DRILL_DOOR`, `DRILL_HUB_WRAP`,
`DRILL_JOIN_URL`, `DRILL_TOKEN_URL` (the token service's `/v1/token` URL; default `ORG_NODE_TOKEN_URL`, else
`http://<tailscale ip -4>:792/v1/token`), `DRILL_IMAGE`, `DRILL_MIN_MB`, `DRILL_CONTAINER_MB`, `DRILL_DOOR_MIN`,
`DRILL_FP_WAIT_S`, `DRILL_JOIN_WAIT_S`, `DRILL_PROBE_WAIT_S`, `DRILL_POLL_S`, `DRILL_GH_REPO`,
`DRILL_AUTHORIZED_KEYS`, `DRILL_WINBOX_SSH`, `DRILL_TS_API`, `DRILL_STAMP`, `DRILL_ALLOW_NONROOT`.
Each has a default that is right on Contabo. `tests/test_w47_drill_join.py` runs the real script
against stub binaries using these.
