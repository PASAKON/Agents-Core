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

## `--local` on Contabo (18:58 TH, verbatim)
```
live 18:58 TH · contabo 8 (+4 workers, local)
running  CONTABO CMO #c7879552 (Mimi EP6 ผลิต เสาร์ 17 ต.ค.)
running  SomPong
running  CONTABO CTO #268a7843
running  CONTABO CTO #3c1f65ae
running  CONTABO CTO #61a8f144 (Haiku 100k price cliff)
running  CONTABO CTO #94be4ec7 (relay TikTok 6-digit fix)
idle     CONTABO CMO #c4432bad
idle     CONTABO CTO #e106b78b (คุม CTO 6 session จนจบ)
send: SendMessage(to=<text after the status>, verbatim). "N agents are named X" → re-send with the [ref] the error marks active.
```
Hub unreachable (`ORG_DB_URL` pointing at 127.0.0.1:1): `live_sessions: hub unreachable (OperationalError) — fall back to ListAgents`, rc 0, no DSN.
15 C-level rows + header + footer, Thai topic on every row: 1,276 chars (1,941 UTF-8 bytes), limit 3,000.

## Real winbox pull (read-only, no hub write)
`pull_remote("winbox")` → `parsed 0 row(s) in 2.4s` (winbox had no live sessions). The PowerShell ran and returned `[]`.

## Costs measured
`ensure_publisher`, lock held: ~105 µs per call. Module import on system python3 3.12: 4–43 ms across three runs, mostly interpreter noise.
