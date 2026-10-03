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
    --why "W4.7 join drill: a throwaway container joins the mesh as drill-<utc stamp>. Your tap IS the human approval of that node. It opens the join door for the run, then creates and revokes one tailnet device, one GitHub deploy key and one Infisical client secret, and pushes one probe branch that it deletes. Needs 1.5 GB free RAM, about 20 minutes. Do not cancel it or restart the Console while it runs: a killed card leaves the node joined (recovery: docs/ops/join-drill.md, If the card was killed)." \
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
preflight, nothing started and nothing written.

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

Preflight also refuses (exit 2) when `CORE/tools/mesh_check.py` has no `--join-drill`: that is a
checkout from before this drill, or not an Agents-Core checkout at all.

## What one run does

| step | what happens | a red here means |
|---|---|---|
| `preflight` | the script is a readable file (it re-runs itself through the hub wrapper, so a pipe is refused); this checkout's `tools/mesh_check.py` has `--join-drill` (the card runs the script at a pushed sha, the tools come from the checkout: a stale checkout is refused here, not after the join); root; `free -m` available >= 1500 MB; docker, curl, gh, git, perl; join door `closed`; no `drill-*` container, volume or non-`left` host; `/etc/infisical/setup.env` exists; `TAILSCALE_OAUTH_CLIENT_ID/_SECRET` in the environment; the Tailscale, `gh` and `node-secrets` readers answer | exit 2, nothing started. The message says which. Memory: Contabo runs one heavy job at a time, run again when it is quiet |
| `door_open` | `deploy/join/door.sh open --minutes 30`. A trap closes it on every exit path, and the door is also closed as soon as `provision` ends | the door service would not start; check `door.sh status` |
| `container` | `ubuntu:24.04`, hostname `drill-<stamp>`, 1200 MB cap, `tailscaled --tun=userspace-networking`, state in a removable volume | docker problem (disk, image pull); nothing joined |
| `mint` | `hq_join mint --host drill-<stamp>`; the token is held in one shell variable | hub unreachable or `ORG_DB_URL` missing; see `docs/ops/hq-join.md` |
| `join` | in the container, `curl -fsSL <hub>/org-join/join.sh -o /tmp/join.sh`, then `sh /tmp/join.sh --host ...` with the token in the **environment** (never argv). Waits for the fingerprint line | join.sh stopped before accept. The detail carries its last log line (masked). Door closed? token expired (20 min)? hub URL wrong? |
| `approve` | `hq_join approve --fingerprint <read from the node>` | fingerprint mismatch: the node's key file and the hub's row disagree |
| `provision` | `ORG_W42_PROVISION=1` set for this one command only; then waits up to 15 min for join.sh to finish (it polls `/sealed`) | `provision` refused: this box lacks the admin identity, or Infisical/Tailscale refused. join.sh stopped: read its last line |
| `node_probe` | join.sh's own step 9 (`node_dispatch.py probe` through the node's identity) must have passed | exit 2 from join.sh: joined but could not probe. Finding `node_probe_failed`. The node has no `ORG_DB_URL` (Org-Node holds only the OAuth token) so this may fail by design; it is reported, the run goes on |
| `token_worker` | on the node: `claude -p` with **only** `CLAUDE_CODE_OAUTH_TOKEN` from Org-Node prod must answer a nonce. Everything else is stripped, and the token never appears on a command line: a `python3 -I -c` one-liner builds the clean environment (PATH, HOME, the token) and `exec`s `claude`, so it reaches the process by environment only | the W4.0 pass criterion failed: token missing from Org-Node prod, wrong scope, or `claude` not installed |
| `probe` | a task for the node is created `pending` (so no poller adopts it); the node commits `docs/ops/mesh-probe/contabo-<host>.md` with a `mesh-probe:` message on `agent/probe-<task>` and pushes; the hub `git ls-remote`s the same sha; <= 15 min. **Never merged.** | finding `deploy_key_read_only` (see gaps), or the node could not reach origin, or the sha on origin differs |
| `leave` | `ORG_W42_PROVISION=1 hq_join leave --host ... --live`. The flag matters: without it `w42_enabled()` is false, every revoker answers "not wired yet: live revocation is off" and nothing is removed | the three real revocations (`infisical_client_secret`, `tailscale_device`, `github_deploy_key`) must be `[ok]`. Only `authorized_keys ... not wired yet` failures are accepted, and they are recorded as finding `leave_partial_authorized_keys_unwired` |
| `verify_tailnet` | Tailscale API: no device named `drill-<stamp>` | `leave` said ok but the device is still there |
| `verify_deploy_key` | `gh api repos/PASAKON/Agents-Core/keys`: no key titled `org-node:drill-<stamp>` | same, for the deploy key |
| `verify_infisical` | `infisical_setup.py node-secrets`: no `live` secret `org-node:drill-<stamp>` | same, for the client secret |
| `verify_host_row` | `hq_join status --host`: row is `left` | see gap 1: `leave()` writes `left` only when every step is ok |
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
| hosts row `drill-<stamp>`, its tailnet device, GitHub deploy key and live Infisical client secret | `join` to `provision` | `hq_join leave --live` |
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
scripts/hub/with-org-db-env.sh env ORG_W42_PROVISION=1 "$PY" -m tools.hq_join leave --host "$H" --live
```

`leave` prints one line per step. `[ok] tailscale_device`, `[ok] github_deploy_key` and
`[ok] infisical_client_secret` must all hold. Until W4.1b (task-8da2f248) merges, each
`authorized_keys` line reads `[FAILED] ... not wired yet` and the row stays `partial` (gap 1 below);
once it merges, run the same `leave` line again and the row becomes `left`. `leave` is safe to repeat:
a credential that is already gone counts as ok.

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
scripts/hub/with-org-db-env.sh "$PY" -m tools.hq_join status | awk -v h="$H" '$1 == h'   # left (partial until W4.1b)
```

## What it proves, and what it does not

Proves, for one throwaway node on one box:

- join.sh, the token, accept, the fingerprint gate, `provision` and the sealed hand-over work end to
  end with a clean machine and no login;
- a node, with only the Org-Node OAuth token, can run `claude -p` (W4.0 criterion);
- a task targeted at the node can be completed by the node and its commit reaches origin, in time;
- `hq leave --live` removes the tailnet device, the deploy key and the Infisical client secret, and
  the script checks each of them directly (Tailscale API, `gh api`, `node-secrets`), not from
  `leave`'s own report.

Does **not** prove:

- that the **hub can dispatch to a joined node**. A joined node has no `mesh_ssh` route yet, so the
  probe's transport is `docker exec`. Hub-to-node dispatch is not exercised;
- a person comparing the fingerprint on two screens (see above);
- a real second machine: the node is a container on Contabo, tailnet in userspace mode;
- that `authorized_keys` cleanup works: nothing writes those keys until W2.8, so "none was ever
  there" is true but weak. Mac is not checked until G2;
- that the node's own `ORG_DB_URL` path works (the node has none).

## Known gaps in the pipeline that a run will hit

These come from reading `tools/hq_join.py` and `deploy/join/join.sh`, offline. A live run settles
each; the script reports them rather than hiding them.

1. **`hq_join leave` cannot mark the row `left` while `authorized_keys` is unwired.** `leave()` adds
   one `authorized_keys` step per other non-left host, each fails with `not wired yet`, and `left`
   is written only when no step failed. So `verify_host_row` is **expected to go red** until W2.8
   ships or `leave()` treats unwired steps differently (a security decision, not the drill's). The
   drill stays strict: it will not wave the row through.
2. **The deploy key is read-only** (`add_deploy_key` registers `read_only=True`), so the node cannot
   push its probe branch: step `probe` fails with finding `deploy_key_read_only`. Options: a
   write-capable deploy key for drill hosts only (CEO call: the repo is public, a write key on a
   throwaway container is a real credential), or another way to return the node's work. Until then
   the "probe commit on origin" criterion cannot pass.
3. **Contabo may not be an admin host.** `provision` needs `/etc/infisical/setup.env`, and the Mac
   is documented as the admin host. Preflight refuses (exit 2) with that message. Agents-Core prod
   must also carry `TAILSCALE_OAUTH_*` and the box needs a `gh` login that can read deploy keys.
4. **Winbox.** Reading `administrators_authorized_keys` needs an admin-capable ssh alias. Set
   `DRILL_WINBOX_SSH`; without one, `verify_authorized_keys` is red (unverifiable).
5. **join.sh step 9** (`node_probe`) reads the hub; the node has no `ORG_DB_URL`. May be red by
   design: finding `node_probe_failed`.

## W4.0 questions this drill answers live

| question | where the answer lands |
|---|---|
| Does `claude -p` work on a node with only `CLAUDE_CODE_OAUTH_TOKEN` from Org-Node prod? | step `token_worker` |
| Does `claude remote-control` start on that token alone? | `w40.remote_control`, `w40.remote_control_error`, and `w40.remote_control_output` (read this: `true` only means it was still running at 25 s) |

## Safety

- No secret is printed, written to the JSON, or put in a command line. The join token lives in one
  shell variable and reaches the container through the environment. The node's OAuth token reaches
  `claude` by environment only (a `python3 -I -c` exec builds the clean env; no `env VAR=...`, no
  `sh -c '... VAR="$VAR"'`), because container processes show in the host's `/proc` and in any
  execve audit. There is no `set -x`. Every
  detail passes a mask for `tskey-`, `sk-ant-`, `AGE-SECRET-KEY-`, `ghp_`-style tokens.
- No `.env` is created. The script re-execs itself through `scripts/hub/with-org-db-env.sh`, like
  every Contabo consumer of the hub.
- It deletes only names it made: `drill-<stamp>` container and volume, the `agent/probe-task-<hex>`
  branch (the name is checked before `push --delete`), and it only cancels its own probe task.
- The probe branch is never merged: the repo is public, and nothing from a throwaway node should
  reach `main`.

## Overrides (tests and odd boxes)

`DRILL_CORE` (default: the git top level of the working directory, else the live checkout),
`DRILL_LIVE_CORE` (the join service's checkout, default `/opt/MoonieXHQ/Agents/Core`; its `.venv` is the
fallback python), `DRILL_STATE_DIR`, `DRILL_ROWS_FILE`, `DRILL_PY`, `DRILL_DOOR`, `DRILL_HUB_WRAP`,
`DRILL_JOIN_URL`, `DRILL_IMAGE`, `DRILL_MIN_MB`, `DRILL_CONTAINER_MB`, `DRILL_DOOR_MIN`,
`DRILL_FP_WAIT_S`, `DRILL_JOIN_WAIT_S`, `DRILL_PROBE_WAIT_S`, `DRILL_POLL_S`, `DRILL_GH_REPO`,
`DRILL_AUTHORIZED_KEYS`, `DRILL_WINBOX_SSH`, `DRILL_TS_API`, `DRILL_STAMP`, `DRILL_ALLOW_NONROOT`.
Each has a default that is right on Contabo. `tests/test_w47_drill_join.py` runs the real script
against stub binaries using these.
