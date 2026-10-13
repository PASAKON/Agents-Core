# live_sessions — task-9c563bea (13 Oct 2026)

One compact list of live C-level sessions across Contabo, Mac and winbox, fed by one standalone
`publish --loop` per host. Design as changed twice by CTO #268a7843 (standalone publisher started
from the hook; winbox pulled over ssh). Ops doc: `docs/ops/live-sessions.md`.

## Files changed
- `tools/live_sessions.py` — NEW. Registry reader, liveness, name/role parse, publisher loop, `ensure_publisher`, ssh pull, reader, CLI.
- `lib/db_pg.py` — `live_sessions` + `live_hosts` (with `error`) in `PG_SCHEMA`.
- `config/hosts.yaml` — contabo: `claude_session_dirs`, `live_sessions_pull: [winbox]`.
- `scripts/hook-inbox.py` — `_ensure_live_publisher()`, called before the drain, C-level only.
- `scripts/live-sessions.sh` — NEW wrapper (org-python, infisical banner filtered, exit code kept).
- `scripts/test_live_sessions.py` — NEW, 100 tests. `scripts/test_hook_inbox.py` — +7 tests.
- `.gitignore` — `state/locks/live_sessions.spawned` (NOT in the declared touches, see Notes).
- `docs/ops/live-sessions.md` (48 lines), this report.

## Tests
```
pytest scripts/test_live_sessions.py scripts/test_hook_inbox.py   -> 109 passed
pytest tests/test_db_init_pg_lock.py tests/test_db_pg_translate.py tests/test_db_backend_pg.py scripts/test_mailbox.py
                                                                  -> 63 passed, 19 skipped (need ORG_TEST_DB_URL)
```
Fail-without-the-fix (fix undone, test run, fix restored, tree clean afterwards):
| fix undone | test that failed |
|---|---|
| procStart comparison → `return True` | `test_a_reused_pid_with_another_starttime_is_skipped` |
| `flock` → `pass` | `test_lock_held_means_a_publisher_is_alive_and_nothing_is_spawned` |
| spawn stamp touched after `Popen` | `test_the_stamp_is_touched_before_the_spawn_so_a_failing_spawn_cannot_loop` |
| failed pull falls through with `rows = []` | `test_a_failed_pull_leaves_the_rows_and_published_at_alone_and_records_the_label` |
| hook gate inverted (workers start it) | `test_a_worker_prompt_never_starts_it` |
| hook lets the publisher print | `test_a_c_level_prompt_starts_the_publisher_even_with_an_empty_box` |

## `--local` on Contabo (18:58 TH; each session topic replaced by `(topic)`, ids and shape kept)
```
live 18:58 TH · contabo 8 (+4 workers, local)
running  CONTABO CMO #c7879552 (topic)
running  SomPong
running  CONTABO CTO #268a7843
running  CONTABO CTO #3c1f65ae
running  CONTABO CTO #61a8f144 (topic)
running  CONTABO CTO #94be4ec7 (topic)
idle     CONTABO CMO #c4432bad
idle     CONTABO CTO #e106b78b (topic)
send: SendMessage(to=<text after the status>, verbatim). "N agents are named X" → re-send with the [ref] the error marks active.
```
Hub unreachable (`ORG_DB_URL` pointing at 127.0.0.1:1): `live_sessions: hub unreachable (OperationalError) — fall back to ListAgents`, rc 0, no DSN.
15 C-level rows + header + footer, Thai topic on every row: 1,276 chars (1,941 UTF-8 bytes), limit 3,000.

## Real winbox pull (read-only, no hub write)
`pull_remote("winbox")` → `parsed 0 row(s) in 2.4s` (winbox had no live sessions). The PowerShell ran and returned `[]`.

## Costs measured
`ensure_publisher`, lock held: ~105 µs per call. Module import on system python3 3.12: 4–43 ms across three runs, mostly interpreter noise.

## Iteration 2 (security review: 1 HIGH, 3 MEDIUM, 2 LOW, 1 doc)

Facts used: `state/` and `state/locks` are group-writable by the secretary account and not sticky;
the publisher runs as root; sompong writes its own registry dir.

| # | sev | change |
|---|---|---|
| 1 | HIGH | `_safe_open()`: `O_NOFOLLOW\|O_NONBLOCK\|O_CLOEXEC` (each via `getattr`), then `fstat` must say a regular file, one link. Used for the lock (pid written through that fd), the spawn stamp (`ftruncate`+`write` on the fd, no `Path.touch`) and the log (fd passed to Popen as stderr, refused → `DEVNULL`). |
| 2 | MED | doc stop command is `pkill -f 'tools.live_sessions publish --loop'`. |
| 3 | MED | `_clean()`: categories Cc/Cf/Zl/Zp → space, runs of spaces collapse, name ≤120 chars; address = cleaned name. `map_status` returns only `running`/`idle`/`unknown`. |
| 4 | MED | `_read_session_file()`: `O_RDONLY\|O_NOFOLLOW\|O_NONBLOCK`, regular file only, ≤64 KiB (exactly 65,536 is read, 65,537 is skipped). |
| 5 | LOW | `ensure_publisher` returns False when `"worktrees"` is in `Path(root).resolve().parts` (also through a symlink). |
| 6 | LOW | `--` before the ssh target in `pull_argv`. |
| 7 | doc | topics in the `--local` block above are `(topic)`. |

### Beyond the list (same class, small)
- `_safe_open(create=True)` opens the parent dir with `O_NOFOLLOW\|O_DIRECTORY` and opens the file relative to it (`dir_fd`, POSIX), so a symlinked `state/locks` is refused too: the secretary can replace that dir, not only the files in it.
- `_clean` also covers `sessionId` (≤64) and the former name; a NUL there failed the whole host's PG transaction the same way.
- `pid` must be `0 < pid < 2**31`: the column is INTEGER, and one record of `10**12` from winbox (no local liveness check) failed the whole winbox publish.
- `RecursionError` is caught where JSON is parsed (a 60k-deep `[[[…` in a session file or in the pull output).

### Tests
```
pytest scripts/test_live_sessions.py scripts/test_hook_inbox.py scripts/test_mailbox.py   -> 177 passed
pytest tests/test_db_init_pg_lock.py tests/test_db_pg_translate.py tests/test_db_backend_pg.py scripts/test_mailbox.py
                                                                                          -> 63 passed, 19 skipped (need ORG_TEST_DB_URL)
```
New tests: a symlink at the lock / stamp / log path (victim file unchanged; lock and stamp: no spawn;
log: spawn with `DEVNULL`); a dangling symlink; a hard link; a symlinked `state/locks`; a FIFO at each of
the three paths (`ensure_publisher` returns within 2 s, run in a thread with a join timeout); worktree
root and a symlink to one; `--` position with a hostile target; hostile name (`\n`, U+0085, U+2028/9,
NUL, U+202E, CR/TAB, 300 chars) → one line, ≤120, row published; NUL in every field → publish succeeds;
status `"pwned\nrunning …"` → `unknown`; pid range; empty session id; the pull path with the same
hostile input; session file as symlink / FIFO / 70 KiB / 64 KiB boundary / deeply nested.

Fix undone, tests run, fix restored (tree clean after each; every run under `timeout`):
| fix undone | result |
|---|---|
| item 1: `_O_SAFE = 0` | 8 failed (lock/stamp symlink, dangling, symlinked dir, log symlink, FIFO at stamp and log, registry link/FIFO) |
| item 1: fstat regular/nlink check → `True` | 2 failed (hard link, FIFO at the lock) |
| item 3: `_clean` only truncates | 11 failed |
| item 3: `map_status` passes any value | 4 failed |
| pid range check dropped | 5 failed |
| item 4: plain `read_bytes()` | 2 failed (link/FIFO/size, 64 KiB boundary) |
| item 5: worktree guard removed | 2 failed |
| item 6: `--` removed | 2 failed |
The first item-1 run showed the stamp-symlink test passing for the wrong reason (the victim was freshly
written, so the "fresh stamp" branch refused before any write). `_victim` now has an old mtime; after that
the stamp case fails without the fix.

### `--local` on Contabo (19:20 TH; topics replaced by `(topic)`, ids and shape kept)
```
live 19:20 TH · contabo 8 (+3 workers, local)
running  CONTABO CMO #c4432bad
running  CONTABO CMO #c7879552 (topic)
running  CONTABO CTO #268a7843
running  CONTABO CTO #3c1f65ae
running  CONTABO CTO #8fb0f1b1 (topic)
running  CONTABO CTO #94be4ec7 (topic)
idle     SomPong
idle     CONTABO CTO #e106b78b (topic)
send: SendMessage(to=<text after the status>, verbatim). "N agents are named X" → re-send with the [ref] the error marks active.
```
A real child process with an fd from `_safe_open` as stderr wrote into the log (mode 0644); the lock held
its pid through the checked fd and a second acquirer got None without wiping it.

### Not checked / risk
- A name longer than 120 characters, or with a Cf character in it (a ZWJ emoji), is shown changed, so
  `SendMessage(to=…)` with that address returns "not found". The id (`#e106b78b`) in the name still says which session it is.
- A live run of `ensure_publisher` in the main checkout was not made: this worktree is refused by item 5, as intended. The spawn path was run with real files and a fake `Popen`, plus one real child for the stderr fd.
- `O_NOFOLLOW` / `dir_fd` / FIFO behaviour is Linux-tested only. macOS should match; on Windows there is no `O_NOFOLLOW` or `dir_fd`, so the checks there are the fstat ones only, and Windows was not run.
- The ssh pull still reads winbox's whole stdout into memory (25 s cap). A compromised winbox could stream gigabytes in that time; not in the review list, not changed.
- Only the last component of the parent is checked. A symlink higher up (for example `state/` itself) is still followed; the dir that holds `state/` is `drwxr-xr-x 501:staff`, so the secretary account cannot swap `state/` for a link, and I did not extend the check.
- Registry dirs are read with a plain `listdir`; a dir with millions of entries is not bounded.
