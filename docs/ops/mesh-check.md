# mesh-check — Org Mesh acceptance test

`tools/mesh_check.py` is the acceptance test for Org Mesh
(`docs/design/org-mesh.md`, plan approved by the CEO 2026-09-28). It prints
the wiring matrix from the design doc's §1 measured tables and exits 1 when a
cell that is expected green for the given `--expect` wave is red. Every wave
adds its own level to check; this build ships the frame plus L0–L8, the SEC
(dispatch-key security) row and the one-poller invariant (INV).

## How to run

### Default mode (Mac)

```bash
.venv/bin/python -m tools.mesh_check --expect w0
```

Runs this host's own L0/L1/L2 checks, collects every other host's L0–L2 via
read-only ssh (`--local --json`, see below), prints the combined markdown
matrix, writes it to `state/mesh-check/<UTC ts>.json` and
`state/mesh-check/latest.json` (both gitignored), then exits 0 if every cell
in scope for `--expect` passed, 1 otherwise. It also computes the two levels
that only read: L8 (a file or the hub's `join_drill` row, from w4) and INV (the hub, from w1). It never
dials a host and never writes the ledger unless `--live` is given.

`--expect wN` is required outside `--local`/`--get-task` — it's the wave
you're claiming, and it decides which cells actually count toward the exit
code (see "Wave gating" below).

### `--local --json` (run on Contabo or winbox)

```bash
python3 -m tools.mesh_check --local --json
```

Prints only this host's own L0/L1/L2 cells as one JSON object, writes
nothing, and makes no delegate/ledger calls. This is what the Mac's default
mode collects over ssh from each peer. It works two ways:

- **Deployed checkout**: `ssh <alias> "<python> -m tools.mesh_check --local --json"`.
- **Not deployed yet** (this branch hasn't been pulled there): the Mac pipes
  the script's own source over stdin —
  `ssh <alias> python3 - --local --json < tools/mesh_check.py`. Every import
  of a repo module is guarded with `try/except`, so a piped copy with no
  filesystem context around `lib/config.py` degrades its cells to "n/a"
  instead of crashing.

### `--live` (delegate and mesh probes — CTO runs this, not you)

```bash
.venv/bin/python -m tools.mesh_check --expect wN --live [--no-merge]
```

Adds L3: for each target host, creates a real probe task, delegates it,
polls for completion, and merges it. This spawns real workers and writes a
real commit — see "L3 in detail" below before running it. `--no-merge` stops
after delegate/poll and skips `merge_task` (useful for inspecting a probe
without landing it).

When L3 and L5 are both claimed for a pair (A = this host, B), L5 runs
**inside L3's window**, on L3's own probe task, so one `--live` run can turn
L5 green and prove the wake (see "L5 — letters"). L3 then sends one extra
letter and its probe task waits up to 120 s for it.

`--live` also computes the mesh levels, for this host's own outbound row and
only for cells `--expect` already claims: **SEC**, **L5**, **L6** and **L7**.
A pair whose L5 ran inside L3's window is not asked again.
They dial real hosts over the dispatch key (`ssh -F none -i
~/.ssh/org_dispatch`, built only by `lib.mesh.build_argv`) and write to the
live hub: SEC (a) and L6 make the far side stamp `hosts.probed_at`, and L5
writes one `letters` row per cell. L6 runs before L7 on purpose: the router
rejects a probe older than 60 s, so L6's fresh stamps are what L7 reads.
Nothing here is run by the unit tests; they mock `subprocess.run` and
`lib.mesh`.

### `--get-task <id> --json`

```bash
python3 -m tools.mesh_check --get-task task-abc12345 --json
```

Reads one task from this host's own ledger and prints it as JSON. This is
what L4 uses on the *target* side — host A creates a task locally, then asks
host B (read-only ssh) to run this against its own ledger and see whether
the task is visible there.

## What each level proves

- **L0 identity** — "which host am I?" Cross-checks `lib.config.self_host()`
  (when it exists — it lands in wave W0.1, so its absence is tolerated, not
  a disagreement), a `tailscale status --json` Self.HostName/DNSName match
  against a configured host key or ssh alias, and whether this checkout's
  `ROOT` equals some host's `agents_root` in `config/hosts.yaml`. Green only
  if every available source agrees. Diagonal only (`from == to`) — there is
  no cross-host "who are you" question.

- **L1 ssh** — from this host to every other host:
  `ssh -o BatchMode=yes -o ConnectTimeout=5 <alias> true` (winbox falls back
  to `cmd /c exit 0` when `true` isn't on PATH). Mac has no ssh alias
  (sshd closed by design) — any cell targeting mac renders
  "closed (by design)" and is excluded from the exit code until wave w2.
  The dispatch-key checks are **not** here: they live in the SEC row below.

- **L2 org MCP** — starts the org MCP server for this host over stdio
  exactly as a C-level session does (`scripts/lib/cxo_mcp_config.py`'s
  command/env), sends `initialize` + `tools/list`, and checks `create_task`
  and `delegate_task` are both listed. Diagonal only — this proves the
  server itself works on this host, not a cross-host property.

- **L3 delegate** (`--live` only) — proves a real cross-host delegate cycle:
  `create_task` → `delegate_task(host=T)` → poll `get_task` until
  review/done (25 min timeout) → `merge_task` → confirm the merge sha is on
  `origin` (`git ls-remote`) and that the cycle left no new tracked change in
  this host's runtime checkout (`git status --porcelain`, before vs after).
  See "L3 in detail" below.

- **L4 ledger** — creates a task on this host's own ledger, then asks
  another host (read-only ssh, `--get-task --json`) whether it sees that
  task. Red today by design — every host still runs its own SQLite
  (`state/tasks.db`), so nothing federates yet. Expected green from wave w1
  once the Postgres hub lands.

- **L5 letters**, **L6 liveness**, **L7 router**, **L8 join drill**, **SEC**
  and **INV** — see "The mesh levels" below, one section each.

## L3 in detail

L3 opens **one** long-lived stdio MCP session and keeps it open across the
entire create → delegate → poll → merge cycle — not a fresh CLI invocation
per step. `delegate_task`'s kickoff and `_verify_claimed` run as background
tasks inside the server process and die with it, so a one-shot-per-step
approach would silently drop them.

Before `create_task` can run, L3 registers a dedicated probe session and
sets a one-line charter through the same code path
`tools/session_charter.py` uses (`lib.db.register_cxo_session` +
`session_charter.set_charter`) — `lib/db.py`'s charter gate
(`_require_charter`) refuses `create_task` for an unregistered/uncharted
session, and `ORG_CHARTER_GATE=off` is a setup/repair escape hatch only,
never used here.

Each probe overwrites exactly one file,
`docs/ops/mesh-probe/<from>-<to>.md`, with a single UTC-timestamped line,
commits with a `mesh-probe:` message prefix, and reports. When L5 runs in
this window, the probe task's description also says that a letter is coming
and tells the worker to wait for it (at most 120 s) and to end its line with
` nonce=<token>`; `roles/probe.md` carries the same rule. L3 reads the file
back from origin for L5 (after the merge it reads `<merge_sha>:<path>`; with
`--no-merge` it reads `origin/<the task's branch>:<path>`), and that read never
changes L3's own verdict. L3 passes only
when: the task reaches `review`/`done`, `merge_task` reports `merged: true`
with a `merge_sha`, that sha shows up in `git ls-remote origin`, and
`git status --porcelain` in this host's runtime checkout has no tracked entry
after the merge that it did not have before the probe started. Dirt that was
already there is not the merge's doing: the Mac's checkout always carries the
harness's model line in `claude-home/settings.json`, and other sessions' WIP
can sit in any checkout for days. New untracked (`??`) entries are ignored
too, because other sessions keep writing state files during the 25 minutes;
`merge_task` can only change tracked files there. Any of `failed` / `blocked_human` /
`conflict` status, a 25-minute timeout, or a missing/absent merge sha is a
hard fail with the specific reason in the cell.

## Wave gating

`EXPECT` at the top of `tools/mesh_check.py` maps `(level, from_host,
to_host) -> first_wave_green`. A cell:

- **absent from `EXPECT`** (e.g. an off-diagonal L0/L2 cell — those levels
  are diagonal-only) always renders `n/a` and never affects the exit code.
- **present but gated to a later wave than `--expect`** renders `n/a` (or
  the literal `closed (by design)` for an L1 cell whose target has no ssh
  alias) — not yet claimed, so not yet judged, and it does **not** fail the
  run.
- **a SEC or L5 cell whose target has no `mesh_ssh`** in `config/hosts.yaml`
  renders `closed (by design)` whatever the wave, is never dialled, and is
  excluded from the exit code. The tool reads `mesh_ssh` from the config; no
  host name is hardcoded. Today only the Mac has `mesh_ssh: null` (its sshd
  opens at the very end, G2), so every cell into the Mac is closed until that
  line is filled in. L6 is closed the same way for a host that has no
  `mesh_ssh` and is not the host the tool runs on (the host that runs it
  answers `probe` in-process).
- **present and in scope for `--expect`** renders one of four texts and
  counts toward the exit code unless it is closed:

  | text | meaning | exit code |
  |---|---|---|
  | `ok` / `ok (<note>)` | the far side answered, and right | 0 |
  | `FAIL(<reason>)` | **red**: the far side answered, and wrong | 1 |
  | `UNREACHABLE(<reason>)` | `lib.mesh.MeshUnreachable` (ssh 255, timeout, no JSON, or the hub itself unreadable): nothing answered, so nothing is known | 1 |
  | `not run (<reason>)` | L8 only: no drill has ever written its file | 1 |

  **Unknown is never green.** Red and unreachable both fail the run but are
  printed apart, so a host that is down is not read as a host that is
  wrong: live, before the dispatch keys are installed on Contabo and
  winbox (W2.8a), every mesh cell reads `UNREACHABLE`, not `FAIL`.

This means running `--expect w0` today never fails on, say, L3
contabo→winbox (gated to w3) even though nothing computes it — but it does
fail on a genuinely broken cell that's already claimed for w0, like L0
disagreeing on a worktree checkout.

## Each row runs from its own host

L3 and L4 can only ever be computed by the host actually executing the
process, for that host's own outbound row — a single invocation of
`mesh_check.py` can prove "mac can delegate to contabo" (it's running on
mac), but it can never prove "contabo can delegate to winbox" from the Mac's
seat. There is no ssh-in equivalent for these two levels the way `--local`
covers L0–L2: a live cross-host delegate or a cross-host ledger read
genuinely has to originate from that row's own host.

Practically: getting a fully green (in-scope) matrix requires running
`mesh_check.py --expect wN --live` **separately on each host**, from that
host's own seat, and merging the three `state/mesh-check/latest.json`
snapshots (or just reading each host's own printed matrix) — never a single
run claiming to speak for every row.

The same rule holds for SEC, L5 and L6: `--live` computes only the row whose
`from` is the host the tool runs on (SEC and L5), and the cell of each host
for L6. L7, L8 and INV are not per-host: they read the hub (or a file), so
any one host's run can claim them.

## The mesh levels

Every cell below follows the three-answer rule in "Wave gating": green, red,
unreachable, and never green on unknown. Every `lib.mesh` call is
`ssh -F none -i ~/.ssh/org_dispatch <options> <mesh_ssh> <verb>`, built only
by `lib.mesh.build_argv`; the admin alias of L1 is never used. The ledger is
the Postgres hub; `state/tasks.db` is a tombstone and is never opened.

### Gate table (the new rows)

`(level, from, to) -> first wave the cell must be green`, as in `EXPECT`:

| level | cell(s) | wave |
|---|---|---|
| SEC | mac→contabo, contabo→mac (closed until the Mac has `mesh_ssh`) | w2 |
| SEC | mac→winbox, contabo→winbox, winbox→contabo, winbox→mac (node_dispatch on Windows is W3.3) | w3 |
| L5 | mac→contabo, contabo→mac | w2 |
| L5 | mac→winbox, winbox→mac, contabo→winbox, winbox→contabo | w3 |
| L6 | mac, contabo (diagonal) | w2 |
| L6 | winbox (diagonal) | w3 |
| L7 | `always_on` → contabo | w2 |
| L7 | `win_gui` → winbox, and stale winbox → `no_host` | w3 |
| L8 | `all` (one cell) | w4 |
| INV | `all` (one cell) | w1 |

L7 is one diagonal cell per host (contabo, winbox), not a pair. L8 and INV
are single cells: in the printed matrix they show as a two-column
`check | result` table, and in `state/mesh-check/latest.json` under
`matrix.L8.all.all` and `matrix.INV.all.all`. INV is gated at w1, the wave in
which the hub lands, because the poller sets it reads only mean something
when every host shares one ledger.

### SEC — the dispatch key gets `probe` and no shell

**Proves**, for every direction whose target has a `mesh_ssh`:

- (a) `mesh.dispatch(to, "probe")` returns `ok: true` and `result.host ==
  to`: the key reaches the right box and the forced command runs.
- (b) the far side refuses a shell. `lib.mesh` refuses a bad verb locally,
  before ssh, so the raw text has to be sent around it: the check takes
  `prefix = mesh.build_argv(to, "probe", ())[:-1]` (every option and the
  destination, minus the verb) and runs `prefix + [payload]` for each of
  `probe; id`, `probe && id`, `$(id)`, a backtick `id`, `probe | id` (the
  five of `docs/ops/node-dispatch.md` acceptance check 2) and `bash`.
  Green needs, for every payload, that the last stdout line is
  node_dispatch's own JSON with `ok: false`, and that `uid=` appears in
  neither stdout nor stderr. `uid=` anywhere is red, even next to a proper
  refusal: a shell that ran `id` and then also printed the refusal is still a
  shell.

**How it can lie:**

- A payload refused **here** is not the far side's refusal. Calling
  `mesh.dispatch` with `probe; id` returns `ok: false` without touching ssh,
  which is exactly what a correct server would answer. The check therefore
  never calls `dispatch` for (b); an answer counts only if it came back from
  ssh as a JSON line. If `build_argv` itself refuses, the cell is red and
  says the far side was not tested.
- ssh exit 255, a timeout or an OSError on any payload is `UNREACHABLE`
  (nothing was tested), never green.
- The refusal check reads node_dispatch's JSON; a far side that prints some
  other JSON object with `ok: false` passes it. The `uid=` search is the
  real guard for the shell; the JSON is the guard for "the forced command
  answered".
- It only proves what these six payloads reach. A key that is not forced to
  node_dispatch at all would run `id` and fail on `uid=`; a restricted shell
  that rejects `id` but allows `ls` would pass. The `command=`, `from=` and
  `restrict` options on the key line in `authorized_keys` stay the
  authoritative control; this row is the regression test, not the control.
- (a) is a real call, so it writes `hosts.probed_at` for the far side on the
  live hub.

**Waves:** see the gate table.

### L5 — letters

**Proves**, for A→B: `deliver_letter` is the verb that carries a letter to a
recipient on B. The check finds the newest in-progress `probe`-role worker
on B (the recipient: a letter needs a live worker session on the box that
receives it), calls `db.create_letter(B, "probe", body, to_session=<its
task id>, from_role="mesh_check", from_host=A)`, then
`mesh.dispatch(B, "deliver_letter", <id>)`. Green needs all of:

- the reply is `ok: true`, for this `letter_id`, with `delivered: true` (its
  `to` must be `probe-<that task id>`) or `already_delivered: true`;
- the hub row now has `status = 'delivered'`;
- the reply does not report a failed wake: `woke: false` with a `why` is red.

The body says it is a mesh-check probe letter and to ignore it, so a human or
a worker that reads it knows to do nothing.

That is the **standalone** form, which runs when L3 is not claimed with L5
for the pair (for example `--expect` below the wave that claims L3, or a
standalone call). It proves the delivery and the hub row and, at best, what
the reply says about the wake. The form that proves the wake is next.

#### L5 inside L3's window (`--live`, L3 and L5 both claimed)

In one `--live` run, L3 creates the only `in_progress` probe worker on B and
finishes it before the mesh levels run, so the standalone form would find no
worker and be red every time. Instead, `tools/mesh_check.py::L5Window` hands
the letter to L3's own task:

1. As soon as L3's poll sees its task `in_progress` on B, the window writes a
   hub letter to that task (`to_session` = the task id, `to_role` = the role
   L3 created it with) and has B deliver it with `deliver_letter`. The body
   carries a fresh nonce, `MESH-NONCE-<16 hex>`, and tells the worker to add
   ` nonce=<nonce>` to the end of its probe-file line.
2. L3's probe task description says a letter is coming, to wait for it (120 s
   at most, `sleep 15` in a loop) and to copy the token from the letter. It
   does **not** contain the nonce: the worker can only get it from the letter.
   `roles/probe.md` says the same.
3. After the merge, L3 reads `docs/ops/mesh-probe/<A>-<B>.md` back from origin
   (`git show <merge_sha>:<path>` after a `git fetch origin`; with `--no-merge`
   it reads `origin/<branch>`).

L5 is green only when **all** of these hold:

- the reply is `ok: true`, for this `letter_id`, `delivered: true`, with `to`
  equal to `<role>-<task id>`, and the hub row is `delivered`;
- the reply says `woke: true` (the tmux nudge reached a live session and tmux
  exited 0 on every call);
- the file on origin carries `nonce=<this letter's nonce>`.

The note on a green cell is `woke, nonce read back from origin`. Each red says
which step failed: a failed wake (with its `why`), a reply with no `woke: true`
(an older `node_dispatch` reports none), a delivery to the wrong recipient, a
probe file that cannot be read back, a file with no nonce ("the worker did not
read the letter"), or a file with another nonce. `UNREACHABLE` means B gave no
answer, or the hub could not be written. A letter that did not land is
abandoned the same way as in the standalone form. The L5 step never changes
L3's own result.

One exception, on purpose: a **Windows** worker is never woken (it reads its
`MAILBOX.md` before every tool call), and `node_dispatch` answers `woke: false`
with no `why`. For a target whose `os` is `windows`, that reply counts as
"wake not applicable" and the cell reads `wake n/a: Windows worker reads
MAILBOX.md, nonce read back from origin`. The nonce is still required, and a
`woke: false` with a `why` is still red. The wake itself is not proven on
Windows; the nonce proves that the worker read its mailbox.

**How it can lie:**

- The wake fields are `woke` (bool) and `why` (str, only when `woke` is
  false). `tools/node_dispatch.py` sets them on every letter path: `_posix_wake`
  for a POSIX worker and a POSIX C-level letter, `_windows_wake` for a Windows
  C-level letter (only with `ORG_WIN_WAKE=1`; off answers `woke: false` with no
  `why`). A worker letter on Windows returns `woke: false` with no `why`.
  `woke: true` means the nudge reached a live tmux session and every tmux call
  exited 0 (`agent_transport.attempt_wake` returns that bool). It does not mean
  the worker has read anything, which is why the nonce is the proof and
  `woke: true` alone is not. The standalone form still accepts a reply with no
  wake field (`ok (wake not reported)`) because a node running an older
  `node_dispatch` sends none; the window form does not.
- `send_to_cxo.attempt_wake` (the POSIX **C-level** wake) must return the bool
  from `agent_transport.attempt_wake`; while it returns `None`, a C-level
  letter on POSIX answers `woke: false, why: "wake reported no result"`. This
  does not touch the probe check, whose recipient is a worker.
- It needs a live worker of role `probe` on B (`status = in_progress`, its
  `host` = B, a tmux session on POSIX or a worktree on Windows). The standalone
  form creates none; with none, the cell is red (`no in_progress probe worker
  on <B>`), not skipped. The window form uses L3's own task, so a task that
  never reaches `in_progress` (it goes straight to `review`, or fails) leaves
  the cell red with `no letter was sent`.
- A letter that does not land is set to `failed` straight away (only a row
  still `pending`; a delivered row is never rewritten), so the watchdog's
  retry cannot hand it to the probe worker later, out of context. A
  delivered probe letter stays in the ledger as the proof.
- `delivered` plus the hub status are two views of the same far-side write,
  so they can agree and both be wrong only if the far side is wrong about
  the hub. It cannot prove the recipient read the letter.

**Waves:** see the gate table.

### L6 — liveness

**Proves**, per host (diagonal): `mesh.dispatch(host, "probe")` answers in
under 60 s (`L6_MAX_S`, measured with a monotonic clock and also passed as
the call's timeout), says it is that host, and afterwards
`db.get_host(host)["probed_at"]` is fresh by `lib.router._probe_problem`,
the router's own staleness rule (its constant is `PROBE_MAX_AGE_S`, also 60 s;
the check holds no copy of that number). The `probe` verb writes
`probed_at` on the far side, so a fresh stamp shows the write reached the
shared hub. The host the tool runs on answers in-process (that is what
`mesh.dispatch` does for its own host), so the Mac is never "closed" for
L6; any other host with no `mesh_ssh` is closed.

**How it can lie:**

- Fresh `probed_at` can come from someone else's probe a second earlier (the
  CTO's, a router run). The answer in the reply and the timing are this
  call's own; the stamp is only "the hub row is not stale".
- An in-process probe on the Mac proves the verb and the hub write, not that
  anything can reach the Mac: it is the Mac's own liveness only.
- The hub being unreadable after a good probe is `UNREACHABLE`, since the
  freshness is then unknown.

**Waves:** see the gate table.

### L7 — router

**Proves**, with `router.pick_host(task, hosts_rows=rows)` on a synthetic
task (`needs:` in the description header, project `mooniex-agents`, runner
pinned to `claude`, never stored) over the live rows from `db.list_hosts()`:

- `needs: always_on` picks `contabo` (w2);
- `needs: win_gui` picks `winbox` (w3);
- with winbox's `probed_at` pushed past the router's limit **in a deep copy
  of the rows**, the same task gets `no_host` (w3): the router has no
  fallback host to quietly use.

The hosts table is never written; the rows list is never mutated.

**How it can lie:**

- It depends on fresh probes. Nothing probes on a timer, so a host that was
  not probed in the last 60 s is rejected as `no probe`, and L7 reads red
  although the router is fine. `--live` runs L6 first for that reason; read
  an L7 red together with the L6 cell of the same host.
- `contabo` for `always_on` and `winbox` for `win_gui` are the two pairs
  the wave plan names; a legitimate change of `provides` in
  `config/hosts.yaml` turns them red and the pairs in `L7_CASES` have to move
  with it.
- A hub that cannot be read makes both cells `UNREACHABLE`.

**Waves:** see the gate table.

### L8 — join drill

**Proves** that `hq join` was drilled end to end on a clean machine within
the last 7 days. This tool does not run the drill (`scripts/drill-join.sh`
does, on Contabo, as one Run Inbox card: see `docs/ops/join-drill.md`); it reads
`state/mesh-check/join-drill.json` (gitignored, written by the drill):

```json
{
  "ok": true,
  "at": "2026-10-20T14:03:00Z",
  "host": "testbox",
  "steps": [{"name": "mint-token", "ok": true}, {"name": "join", "ok": true}]
}
```

| field | type | meaning |
|---|---|---|
| `ok` | bool | the drill as a whole passed |
| `at` | ISO-8601 string | when it finished; `Z` or an offset, UTC if neither |
| `host` | non-empty string | the machine that was joined |
| `steps` | list of `{"name": str, "ok": bool}` | what ran, in order; may not be empty |

- missing file: the newest `events` row of kind `join_drill` is judged instead
  (the drill records the same JSON there, so the Mac, which never runs the
  drill, can read the cell; the file wins when both exist). No file and no
  row, or a hub that cannot be read: `not run` (a failing, named state, never
  green);
- unreadable, not a JSON object, or a missing or mistyped field: red;
- `at` more than 7 days ago (`JOIN_DRILL_MAX_AGE_S`), or in the future by more
  than 10 minutes: red;
- `ok: false`: red, naming the failed step when there is one;
- `ok: true` with no steps, or with a step that is not `ok`: red, because
  the file contradicts itself.

**How it can lie:** it trusts the file. A drill that writes `ok: true`
without having run, or a stale file copied from another box, passes. It says
which host and how many hours ago in the cell, so a human can see.

**Waves:** w4.

### INV — one poller per remote row

**Proves**, read-only, that every remote or external row has exactly one
poller. For every `in_progress` task that is *remote* (its `host` is set and
differs from its `dispatcher_host`) or whose runner is `codex` or `agy` (a
launcher run: `runners.branch_poller.EXTERNAL_RUNNERS`), it counts the hosts
in `config/hosts.yaml` whose `branch_poller.in_poller_set(task)` is true,
evaluating each in turn with `self_host()` pinned to that host. Green =
exactly 1 for every row. A row with 0 (nobody watches it, it would sit in
`in_progress` for ever) or more than 1 (two pollers flip it twice) is
printed by task id with its poller hosts, e.g. `task-1234abcd (0 pollers)` or
`task-5678abcd (2 pollers: mac, winbox)`, and the cell is red.

`self_host()` is cached and `branch_poller` / `worker_reap` bind it by name
(`from lib.config import self_host`), so the check pins it through
`ORG_HOST` and clears the cache, and puts both back afterwards; patching the
module attribute would not reach them. The hosts table and the tasks table
are never written.

**How it can lie:**

- It evaluates the predicate, not the processes: a poller that is down, or a
  host that runs the predicate differently because its checkout is behind,
  still counts as one. It proves the design has exactly one watcher per row,
  not that the watcher is alive (that is L6).
- A row with no `dispatcher_host` (written before the column existed) is
  claimed by every host except its own, so it shows as `2 pollers`. That is
  a real double poll, not a false alarm.
- At most 500 in-progress rows are read.

**Waves:** w1.

## Later waves

L5–L8, SEC and INV are built; what they need to turn green is not in this
file:

- **W2.8a** — install the dispatch key on Contabo and winbox. Until it is
  there, every live SEC, L5 and remote L6 cell reads `UNREACHABLE`.
- **G2** — open the Mac's sshd and set `mesh_ssh` for `mac` in
  `config/hosts.yaml`. The cells into the Mac then stop being "closed (by
  design)" with no change to this tool.
- **A probe worker per target** for the standalone L5 (see its section). In a
  `--live` run, L3's own probe task is that worker. The wake field on the POSIX
  and worker letter paths of `node_dispatch` exists now (task-f9d23d0b), so L5
  inside L3's window proves a wake and not only a delivery; every target must
  run that `node_dispatch` first.
- **The join drill** (W4.7 in the plan, a container on Contabo; built, `scripts/drill-join.sh`,
  `docs/ops/join-drill.md`, but not yet run live), which writes `state/mesh-check/join-drill.json` and a
  `join_drill` events row; L8 stays `not run` until a run lands.
- Any later wave that adds a level adds it to `LEVELS`, `EXPECT` and this
  file together, without touching the cells above it.

## Troubleshooting

- **`.venv missing`** — L2/L3 need this host's own `.venv` (
  `python -m venv .venv && ./.venv/bin/pip install -r requirements.txt`).
- **`mcp package unavailable`** — same fix; `mcp` is in `requirements.txt`.
- **L0 "sources disagree"** — usually means you're running from a worktree
  or an unregistered checkout, so `ROOT` doesn't match any `agents_root` in
  `config/hosts.yaml`. Expected and honest, not a bug in the tool — run from
  the registered checkout to get a clean L0.
- **L1 timeout / ssh failed** — check the alias resolves
  (`ssh -G <alias>`), and that BatchMode auth (a working key, no password
  prompt) is set up for it.
- **A peer's L0/L2 cells read `no repo access` or a surprising `mcp package
  unavailable` reason, but that host looks fine in person** — the piped
  fallback (`ssh <alias> python3 - --local --json < tools/mesh_check.py`)
  runs that host's *system* `python3`, not its `.venv/bin/python`, because
  the branch hasn't been deployed there yet for `-m tools.mesh_check` to
  work. Whatever's importable system-wide on that box (a missing `pyyaml`,
  or a same-named but different `mcp` package with no `ClientSession`)
  leaks into the result. This clears itself once the peer has this branch
  merged and its own `.venv` — no fix needed in the tool itself.
