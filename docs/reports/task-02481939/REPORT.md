# task-02481939 — Org Mesh W2.2: `tools/node_dispatch.py`

## What was built

`tools/node_dispatch.py`, the single forced command an `org_dispatch` ssh key may run
on a host (`docs/design/org-mesh.md` W2). A caller can name a hub row, never send a
shell.

- Input `SSH_ORIGINAL_COMMAND`, else `sys.argv[1:]`. `shlex.split`. Refused at parse
  time: empty, over 256 chars, any control character (NUL, newline, tab), unbalanced quotes.
- Output exactly one ASCII JSON line. Exit 0 ok, 2 refusal (nothing ran), 1 ran and failed.
  fd 1 is pointed at stderr while a verb runs (fd 0 at /dev/null), so a print or a child
  process cannot share the channel with the JSON line.
- Seven verbs, fixed table, `re.fullmatch` on explicit `[0-9a-f]` classes:
  `probe`, `pid_alive`, `spawn_worker`, `kill_worker`, `start_clevel`,
  `deliver_letter`, `publish_branch`. Role comes from `policies/agents.yaml` `c_level` only.
- Every call writes one `events` row (actor `node_dispatch`, kind `dispatch`), refusals
  included. Unparseable input logs the raw string truncated to 256. A failed audit write
  is reported on stderr and never changes the result.
- In-process `dispatch(verb, args) -> dict` for W2.3 (synchronous; wrap in
  `asyncio.to_thread`).

Every backend is a module that already exists (`tools.delegate`, `tools.worker_reap`,
`tools.send_to_cxo`, `tools.tmux_session`, `lib.mailbox`, `lib.db`). Nothing was
re-implemented. `runners/mac_agent.py` is untouched.

## Design decisions worth a reviewer's eye

1. **`pid_alive` treats `PermissionError` as alive.** `worker_reap._pid_alive` treats it
   as dead, which is right for a reaper that must not signal a stranger and wrong for a
   liveness answer. Own helper, own test.
2. **`authorized_keys` needs `cd <agents_root> &&`.** `-m tools.node_dispatch` only
   imports from the repo root, and sshd starts the command in `$HOME`. Exact lines in
   `docs/ops/node-dispatch.md`.
3. **`spawn_worker` on a non-mac host** goes through `delegate_task`, which on a host
   that is not the Mac has a `_spawn_remote` ssh path. `node_dispatch` passes
   `host=<self>`, so the local launcher is chosen; the ssh path is not reachable from
   here. Not verified against a live Contabo (ADR 0021: no ssh in tests).
4. **`probe` writes only probe fields** through `upsert_host` (version, running,
   free_gb, probed_at). It leaves `os`, `agents_root`, `max_workers` and the join-state
   `status` alone.
5. **`deliver_letter` is idempotent by row status.** A second call returns
   `already_delivered` before touching the mailbox, the wake, or the attempts counter.
   Unsafe `to_session`/`from_role` values from a row are refused before any path is built.
   A dead target session is a Failure and records the attempt (5 attempts flips the row
   to `failed`, existing `lib.db` rule).
6. **`start_clevel`**: Mac uses the existing `spawn-cxo.sh`/`spawn-cto.sh` (iTerm). Any
   other non-Windows host spawns `cxo-claude.sh` in tmux with a generated session id. A
   `--resume <8 hex>` only reaches the shell as a full UUID that `session_status`
   resolved on this host. Windows is refused until W3.
7. **`publish_branch`** pushes `origin <task's own branch>` only: task must be on this
   host, status `review`, branch matches `agent/<role>-<that task id>`, worktree
   resolves inside this host's worktrees root and exists. argv list, never force.

## Verification

| check | result |
|---|---|
| `pytest tests/test_node_dispatch.py` | 126 passed |
| full suite (`pytest`, background, no `-q`/`-x`) | 3248 passed, 27 skipped, 0 failed, 202 s |
| baseline before this task | 3122 passed, 27 skipped, 0 failed |
| `python scripts/test_org_tools_registry.py` | `ALL PASS` |

Test coverage: parser fuzz (56 hostile strings: injection, control chars, Unicode
lookalikes, wrong arg counts, 257 chars; each must exit 2, reach no backend and write one
event row); each verb's happy path with backends replaced by a recorder; `deliver_letter`
twice; wrong-host letter/task refusals; ok and refused `events` rows; a real-subprocess
test that a noisy backend still leaves exactly one JSON line on stdout. tmp_path SQLite
ledger throughout, as in `tests/test_db_hosts_letters.py`.

## Not done / not verifiable here

- The winbox `authorized_keys` line is untested (default shell there is cmd; the
  Administrators-group key file differs). Marked UNVERIFIED in the ops doc for W2.8.
- No real ssh round trip, no real Postgres, no real `tasks.db` (rules). The hub path
  (`ORG_DB_URL`) goes through the same `lib.db` helpers but was not exercised.
- `start_clevel` on Linux and the iTerm path are tested with `subprocess.run` and the
  tmux helpers replaced; no pane or window was opened.
- `pid_alive` and `start_clevel` on Windows are explicit refusals (W3.3 / W3).

## Files

- `tools/node_dispatch.py` (new)
- `tests/test_node_dispatch.py` (new)
- `docs/ops/node-dispatch.md` (new, 79 lines)
- `docs/reports/task-02481939/REPORT.md` (this file)
