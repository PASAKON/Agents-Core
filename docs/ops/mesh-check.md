# mesh-check — Org Mesh acceptance test

`tools/mesh_check.py` is the acceptance test for Org Mesh
(`docs/design/org-mesh.md`, plan approved by the CEO 2026-09-28). It prints
the wiring matrix from the design doc's §1 measured tables and exits 1 when a
cell that is expected green for the given `--expect` wave is red. Every wave
adds its own level to check; this build ships the frame plus L0–L4.

## How to run

### Default mode (Mac)

```bash
.venv/bin/python -m tools.mesh_check --expect w0
```

Runs this host's own L0/L1/L2 checks, collects every other host's L0–L2 via
read-only ssh (`--local --json`, see below), prints the combined markdown
matrix, writes it to `state/mesh-check/<UTC ts>.json` and
`state/mesh-check/latest.json` (both gitignored), then exits 0 if every cell
in scope for `--expect` passed, 1 otherwise.

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

### `--live` (delegate probes — CTO runs this, not you)

```bash
.venv/bin/python -m tools.mesh_check --expect wN --live [--no-merge]
```

Adds L3: for each target host, creates a real probe task, delegates it,
polls for completion, and merges it. This spawns real workers and writes a
real commit — see "L3 in detail" below before running it. `--no-merge` stops
after delegate/poll and skips `merge_task` (useful for inspecting a probe
without landing it).

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

- **L2 org MCP** — starts the org MCP server for this host over stdio
  exactly as a C-level session does (`scripts/lib/cxo_mcp_config.py`'s
  command/env), sends `initialize` + `tools/list`, and checks `create_task`
  and `delegate_task` are both listed. Diagonal only — this proves the
  server itself works on this host, not a cross-host property.

- **L3 delegate** (`--live` only) — proves a real cross-host delegate cycle:
  `create_task` → `delegate_task(host=T)` → poll `get_task` until
  review/done (25 min timeout) → `merge_task` → confirm the merge sha is on
  `origin` (`git ls-remote`) and this host's runtime checkout is clean
  (`git status --porcelain`). See "L3 in detail" below.

- **L4 ledger** — creates a task on this host's own ledger, then asks
  another host (read-only ssh, `--get-task --json`) whether it sees that
  task. Red today by design — every host still runs its own SQLite
  (`state/tasks.db`), so nothing federates yet. Expected green from wave w1
  once the Postgres hub lands.

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
commits with a `mesh-probe:` message prefix, and reports. L3 passes only
when: the task reaches `review`/`done`, `merge_task` reports `merged: true`
with a `merge_sha`, that sha shows up in `git ls-remote origin`, and this
host's checkout is clean afterward. Any of `failed` / `blocked_human` /
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
- **present and in scope for `--expect`** renders `ok` or `FAIL(<reason>)`
  and counts toward the exit code.

This means running `--expect w0` today never fails on, say, L3
contabo→winbox (gated to w3) even though nothing computes it — but it does
fail on a genuinely broken cell that's already claimed for w0, like L0
disagreeing on a worktree checkout.

## The "one poller per remote row" invariant

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

## Later waves

This build ships L0–L4. Each later wave in `docs/design/org-mesh.md` §5 adds
its own level to the same matrix, without touching what's already here:

- **L5 letters** — hub mailbox delivery (a message written on one host is
  readable from another).
- **L6 liveness** — `node_agent` heartbeat / presence per host.
- **L7 router** — pull-model task routing across the hub, not just a single
  delegate call.
- **L8 join drill** — the `hq join` flow for registering a brand-new
  machine end-to-end.
- **A security cell** — auth/authorization boundary between hosts (who is
  allowed to delegate to whom, who can read whose ledger) gets its own row,
  separate from the plumbing cells above it.

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
