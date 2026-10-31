# REPORT task-c02aee60

## Iteration 7 (CTO Main merge gate 2b on PR #617)

`tools/host_queue.py` runs as root from the watchdog and opens `state/host_queue.lock` and
`state/host_queue.jsonl`; `state/` is group-writable. Both opens used to follow a link or wait on a pipe
(`open("a")` for the lock, `disk_queue._load` / `_save` for the queue).

- `tools/host_queue.py`: no longer calls `disk_queue._load` / `_save` (`disk_queue.py` is untouched).
  - Lock: `safe_file._open(..., O_RDWR|O_CREAT, mode=0o600, single_link=True)`, then `fcntl.flock` on that fd;
    closing the fd drops the lock.
  - Read: `safe_file.read_text(QUEUE_PATH, 1 MiB)`, JSON lines parsed as before. A missing file is `[]`. A line
    that is not JSON, or has no `task_id`, is skipped (the old code raised `KeyError` on the second case).
  - Write: `safe_file.write_text_atomic`. New public `load()` replaces the tests' use of `host_queue.disk_queue`.
- `lib/safe_file.py`: new `write_text_atomic(path, text, mode=0o600)`. Temp file `.<name>.<pid>.<rand>.tmp`
  opened `O_EXCL|O_NOFOLLOW` through the folder's fd, written, fsync'd, then `os.replace(src_dir_fd=dfd,
  dst_dir_fd=dfd)`, then the folder is fsync'd. A link or pipe at the target name is replaced, never followed or
  written through. On failure the temp file is removed and the old file is untouched.
- A refused file raises `OSError` (`safe_file.Unsafe`) out of `enqueue` / `drain` / `load`. The watchdog already
  catches it (`watchdog host queue drain error`). In `delegate_task` the error goes to the caller and the task stays
  `pending` with its `delegate_log` set, so a task is not silently lost.

Tests (`tests/test_router.py`; names state the guarantee):

- `test_queue_round_trip_leaves_only_its_two_files` (mode 0600, same task twice = one entry, no temp left)
- `test_queue_refuses_a_planted_link_at_the_lock`, `test_queue_refuses_a_second_hard_link_at_the_lock`
- `test_queue_does_not_follow_a_link_at_the_queue_file[enqueue|drain|load]` (target text unchanged)
- `test_queue_refuses_a_pipe_at_either_file_without_waiting[queue.jsonl|queue.lock]` (5 s guard thread)
- `test_atomic_write_replaces_a_link_at_the_name_and_leaves_its_target_alone`
- `test_atomic_write_keeps_the_old_file_and_no_temp_file_when_it_fails`
- Three existing assertions in `test_router.py`, `test_router_hub_only.py`, `test_w26_pick_host.py` read the queue
  with `host_queue.load()` instead of `host_queue.disk_queue._load(...)`; no expectation changed.

```text
env -u ORG_DB_URL /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q -o addopts='' \
  tests/test_router.py tests/test_router_hub_only.py tests/test_w26_pick_host.py
120 passed in 9.01s
tests/test_portfolio_collector.py (the other `safe_file` user): 55 passed
```

Mutation check (each undone after, files compared byte for byte): lock opened with plain `os.open`; lock without
`single_link`; queue read with `Path.read_text`; atomic write replaced by a plain write; temp file left behind on
failure. Each made at least one of the new tests fail. `git diff --check` clean.

### Not checked / risk (iteration 7)

- Only the three named files plus `test_portfolio_collector.py` were run. The 10 files of iteration 6 and the rest of
  the suite were not re-run after this change; `host_queue` is used by `tools/delegate.py` and `runners/watchdog.py`,
  both read but not changed.
- The folder (`state/`) itself being a link is refused by `O_DIRECTORY|O_NOFOLLOW` in `_open` and `write_text_atomic`,
  but `_locked` calls `mkdir(parents=True, exist_ok=True)` first; that call was not tested with a planted folder.
- A queue file with a second hard link is still read (the brief asked for `read_text` only). It is safe to read, and
  the next save replaces the name with a fresh file, so the other link keeps the old bytes.
- Not run as root and not on the Postgres hub. The tests use a plain tmp folder, so permission and group-writable
  behaviour were not exercised. Pipe refusal relies on `O_NONBLOCK`, tested on Linux only.
- A stale `.host_queue.jsonl.*.tmp` is left only if the process is killed between creating and renaming it; nothing
  sweeps those.

## Iteration 6

PR #617 CI: 93 failures in six files the earlier iterations never ran. Branch
`agent/codex-task-c02aee60`, started at `e7700445` (PR head `03db02bc` merged with main `067da6f6`).

## What changed (iteration 6)

Cause 1 — `lib/router.py pick_host` had been rewritten onto live `host_fill` probes. It is now the
hub-row router again, with the CEO host-fill rule added as one more filter.

- Kept, in the old order: probe age (`probed_at` ≤ 60 s), `status`, `provides` against the header
  `needs:` line (a `needs:` further down a pasted block is still ignored), `running`/`max_workers`,
  unknown project / `paths.<host>`, then runners. Reasons are the old texts: `no_host: …`,
  `no probe ≤60 s …`, `full 3/3`, `provides lacks …`, `router error: …`.
- Added (`_cap_reason`, after the old checks): project in `router.never_on` for the host
  (ExpertAdvisor never on winbox, even when pinned), winbox free RAM under 4 GB (unknown RAM
  also fails), Project Head on winbox while the PC lease is held or unknown, and fill at or
  above `fill_limit_pct` (80). CPU exception for work pinned to Contabo (CPU highest, RAM and
  disk under 80 %, ≥ 1.6 GB free RAM, one job org-wide through the DB slot; an unreadable slot
  fails closed).
- Ordering: Contabo first while it passes, then lowest fill (no reading ranks last), then fewest
  running workers, then most free RAM, then name.
- Rows: hub rows and `host_fill.probe` rows are both accepted (`_hub_shape`). A row with fill
  sensors (any of `ram_total_gb`, `disk_total_gb`, `cpu_pct` present) is judged on fill; a missing
  sensor makes winbox and the Mac not eligible, Contabo keeps the old rule while the readings it has
  are under 80 %. A hub-only row with no fill sensors is judged by the old checks alone, so the old
  contract tests run unchanged.
- Production (`hosts_rows=None`): read the hub table, probe Contabo live, and probe winbox and the
  Mac live (parallel, 10 s) only when Contabo does not take the task. A host that does not answer is
  `status offline (no answer to the live probe)`. The hub keeps the join state and `provides`.
- A task that names its host is judged on that host alone: never moved, same checks. No survivor:
  `no_host: …`; `delegate` queues it in `tools/host_queue.py` (existing watchdog drain, no new timer).

Cause 2 — `tools/node_dispatch.py verb_spawn_ph`: Linux is refused again (Contabo spawns locally).
`tools/spawn_ph.py`: `MESH_HOSTS == ("winbox", "mac")` again; a new `PH_HOSTS` (adds contabo) feeds
`spawn --host`. The `mesh` command dispatches straight to the named host as before ("<host> did not
answer over the mesh: …" kept) and runs the picker, pinned to that host, only when the router is on.
`spawn()` now reports an unreachable remote as that same text instead of a traceback.

Cause 3 — `tools/delegate.py`: the local bash launcher is linux-only again (an agy task on the Mac's
own host goes to `_spawn_local`; a dry run stamps nothing). The darwin remote launcher through the mesh
and `--org-host` stay.

Cause 4 — `runners/relay_mcp_server.py spawn_c_level`: the unknown-role check now runs before the
CTO gate, so `"CTO"` is still "unknown role" and the Contabo-only rule applies to the role `cto`
alone. Every other role keeps its reasons.

## Test changes (each one, and why)

Changed because the CEO rule makes the old expectation wrong:

- `test_w26_pick_host.py::test_lowest_load_wins` → `test_contabo_is_first_while_it_passes` (Contabo
  first even when another host is lighter) plus `test_lowest_load_wins_among_the_rest` (Contabo
  offline). Same for `test_load_tie_breaks_on_more_free_ram`, `test_unknown_ram_loses_the_tie`,
  `test_unknown_load_ranks_last_but_is_still_eligible` (Contabo made unavailable so the old ranking
  is still tested among the rest) and `test_flag_on_pick_of_this_box_takes_the_local_spawn` (Contabo
  made full). New: tie goes to fewer running workers.
- `test_flag_on_explicit_host_and_tasks_host_win_and_are_manual` →
  `…_are_kept_and_checked`: a named host is still never moved, but ExpertAdvisor-on-winbox, the 4 GB
  floor, the cap and the 80 % limit apply to it, so `pick_host` is called and the log reads
  `host: …`, not `manual: …`. New: a full named host is queued, not swapped for a free one.
- `test_w25_spawn_c_level_mesh.py`: the generic mesh tests (dispatch args, bad resume id, unknown
  host, unreachable, rate limit, parallel switch, flag-off mac queue) now use `cmo`; Contabo tests,
  the bad-role list and the "Known: cto, cmo…" text keep `cto`. New: `cto` on winbox/mac is refused
  before any dispatch (mesh on, mesh off, emergency flag set).

Changed for isolation or API shape only (no expectation changed):

- `test_w26`'s `flow` fixture stubs `router._live_rows` (hub rows only, no probe of the test
  machine) and points `host_queue.QUEUE_PATH` at tmp (it wrote `state/host_queue.jsonl`).
- `tests/test_router.py` (this branch's own): fixture patches `config.projects` and
  `db.list_hosts`; "queued for host" → `no_host:`; the partial-sensor test splits Contabo (passes
  while the known readings are under 80 %) from winbox/Mac (not eligible); the probe test now shows
  Contabo-only probing when Contabo takes the task and 3 probes when it does not. New: an unreadable
  CPU-exception slot fails closed.
- `tests/test_router_hub_only.py`: the mesh CLI test turns the router on and checks a refusal.

## Files changed

- `lib/router.py`, `tools/spawn_ph.py`, `tools/node_dispatch.py`, `tools/delegate.py`,
  `runners/relay_mcp_server.py`
- `tests/test_w26_pick_host.py`, `tests/test_w25_spawn_c_level_mesh.py`, `tests/test_router.py`,
  `tests/test_router_hub_only.py`
- This report. Earlier iterations' files (hosts.yaml caps, `host_fill`, `host_queue`, `clevel_gate`,
  launchers, watchdog drain) are unchanged by this iteration.

## Validation

```text
env -u ORG_DB_URL /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q -o addopts='' \
  tests/test_w26_pick_host.py tests/test_w25_spawn_c_level_mesh.py tests/test_node_dispatch_spawn_ph.py \
  tests/test_mesh_check.py tests/test_w03b_local_launcher.py tests/test_w211_directives.py \
  tests/test_router.py tests/test_router_hub_only.py tests/test_org_p2_launchers.py tests/test_node_dispatch.py
712 passed in 64.60s
```

Before: 93 failed, 611 passed (the CTO's per-file counts matched). Mutation check, each reverted
after: `>= limit` → `>`, winbox floor off, `never_on` off, Contabo-first off, pin ignored, CTO gate
off, Linux back in `verb_spawn_ph` — each made at least one test fail. `git diff --check` clean;
gitleaks on the commit: no leaks.

Read-only smoke on Contabo (hub stubbed): the real local probe gives RAM 7.76 GB total / 2.70 free,
disk 71.6 total / 16.6 free, CPU 119 % (load-based) → fill 119 % (cpu). A task pinned to Contabo
reached the CPU exception, and the slot read failed because this sandbox has no hub: it fails closed
(this found the unguarded slot read, fixed above).

## Not checked / risk

- No live winbox/Mac probe, ssh or launch. The remote branch of `_live_rows` + `_merge_live` (mesh
  `probe` facts → hub row) is exercised with fakes only; the `ceo_hold` and `runners` fact names are
  the ones `verb_probe` and `host_fill.probe` write today.
- The CPU-exception slot (`locks` table) was tested on SQLite only, not on the Postgres hub.
- Not run: the rest of the suite (CI owns it) and any other file that imports `lib.router`. Callers
  checked by grep: `tools/delegate.py _route_host`, `tools/spawn_ph.py pick_ph_host`,
  `tools/mesh_check.py` L7 (hub rows, passes).
- If `ORG_HOST_ROUTER` is switched on today, Contabo reads 119 % CPU, so new work would leave
  Contabo for winbox/Mac, or wait for the CPU exception (Contabo-pinned work only). That is the rule
  working, but the switch should be flipped knowing it.
- A hub-only row (no fill sensors) skips the fill filter. Production rows come from a live probe and
  always carry the sensors; a caller passing bare hub rows to `hosts_rows=` gets the old checks only.
- `main` is now `2273ee8b`, ahead of the merge at `067da6f6`; not re-merged here. The
  `config/projects.yaml` difference against current main comes from main's newer commits, not from
  this branch.

## Blockers

- none

## Skill learning

- MISSING [roles/developer.md §Pre-work Checklist 5] : the checklist says to list the tests covering a function you touch but not to run them before the first commit; iterations 1-4 rewrote `pick_host` and ran only the two new test files · evidence: task-c02aee60, PR #617 CI 93 failures in 6 files; `grep -rl pick_host tests/` finds them in seconds
- COSTLY [no owner] : a test that reaches `host_queue.enqueue` without patching `QUEUE_PATH` writes `state/host_queue.jsonl` into the worktree (untracked, not in .gitignore) · evidence: task-c02aee60 first full run · prevented by: patch the path in any fixture that goes through `delegate_task` with the router on
