# task-f9d23d0b — L5 green in one `--live` run, with the wake proven

Branch `agent/developer-task-f9d23d0b`. Runner override: claude (it changes a
security-core verb, `tools/node_dispatch.py`, and builds on another worker's
code, IRON §59).

## What changed

1. `agent_transport.attempt_wake` returns a bool. True only when the nudge
   reached a live tmux session and every tmux call exited 0 (Windows: the
   wake script reported keys sent). It still never raises and never changes a
   caller's success; existing callers keep ignoring the value.
2. `node_dispatch` POSIX worker and POSIX C-level letter paths add `woke`
   (bool) and, when False, `why`. `why` is one of: `wake raised <Type>`,
   `tmux nudge not delivered (...)`, `wake reported no result`. Windows paths
   are untouched.
3. `mesh_check`: when L3 and L5 are both claimed for (A, B), L5 runs inside
   L3's window (`L5Window`). Once L3's task is `in_progress` on B, the window
   writes the letter to that task. The body carries `MESH-NONCE-<16 hex>`; the
   task description does not (it only says a letter is coming and to copy the
   token). L5 is green only if the reply delivered this letter, the hub row is
   `delivered`, `woke` is true, and the probe file read back from origin
   (`git show <merge_sha>:<path>`, or `origin/<branch>` with `--no-merge`)
   carries `nonce=<this nonce>`. With no L3 window L5 is unchanged.
4. `roles/probe.md` and `docs/ops/mesh-check.md` match. The probe still touches
   exactly one file.

## Files changed

- `tools/agent_transport.py` — `attempt_wake` returns bool; windows branch returns the wake's `woke`.
- `tools/node_dispatch.py` — `_posix_wake`; `woke`/`why` on POSIX worker and C-level replies.
- `tools/mesh_check.py` — `L5Window`, `l5_window_for`, `_git_show_from_origin`, `run_l3_probe(..., l5=)`, `_l5_deliver(need_wake=)`, `build_matrix` and `_run_mesh_levels` wiring.
- `roles/probe.md` — nonce-letter wait and the `nonce=` suffix.
- `docs/ops/mesh-check.md` — `--live`, L3 in detail, L5 window form, later waves.
- `tests/test_l5_e2e.py` — new, 45 cases.
- `tests/test_node_dispatch.py`, `tests/test_w35_wake.py` — `woke`/`why` and bool-return tests; POSIX source hash re-pinned.

## Tests

- `tests/test_l5_e2e.py` (new): the whole window with a fake MCP session, a
  fake far side that also plays the probe worker, fake git and a tmp_path
  hub. Green, each red step alone, unreachable, L3 failing, `--no-merge`,
  Windows exception, `build_matrix` wiring, no-window behaviour, git read
  edges, role file in step with the description tail.
- `tests/test_node_dispatch.py`, `tests/test_w35_wake.py`: bool return on every
  path, hash re-pinned (old value kept in the comment), `woke`/`why` on
  C-level and worker paths.
- No live ssh, hub or worker.

## Open: three files outside `touches` (CTO decision)

The self-repo guard (ADR 0020) blocked `tools/send_to_cxo.py`. I did not retry
another route and sent the CTO one `dev_message` naming all three. No answer
yet.

1. `tools/send_to_cxo.py:315` — `attempt_wake` returns None, so a POSIX
   **C-level** letter reports `woke: false, why: "wake reported no result"`
   even when tmux was nudged. Worker letters (the L5 probe path) are
   unaffected. Fix:
   ```diff
   -def attempt_wake(role: str, session_id: str, label: str) -> None:
   +def attempt_wake(role: str, session_id: str, label: str) -> bool:
   ...
   -    agent_transport.attempt_wake(session, label, "send_to_cxo", send_fn=_wake_tmux_send)
   +    return agent_transport.attempt_wake(session, label, "send_to_cxo", send_fn=_wake_tmux_send)
   ```
2. `tests/test_w35_wire.py:241` — asserts the POSIX C-level reply has no `woke`
   key. Its stub returns None, so the reply now has `woke: False, why: "wake
   reported no result"`. With fix 1, make the stub
   `lambda *a, **kw: woken.append(a) or True` and assert `"woke": True`.
3. `tests/test_w33_node_dispatch_windows.py:697` — asserts the POSIX worker
   reply has exactly three keys. Make the `agent_transport.attempt_wake` stub
   return True (`wakes.append(...) or True`) and assert `"woke": True`.

Items 2 and 3 are failing tests today: the brief's own item 2 (`woke` on the
POSIX paths) collides with their old equality asserts.

## Deviations to review

- A Windows worker is never woken, and `node_dispatch` answers a bare
  `woke: false`. In window mode that counts as "wake n/a" (green note
  `wake n/a: Windows worker reads MAILBOX.md, nonce read back from origin`),
  but only for a target whose `os` is `windows`, and the nonce is still
  required. Everywhere else `woke: true` is required.
- The window form needs the target to run the new `node_dispatch`. An older
  one sends no `woke`, which is red ("the wake is not proven"), on purpose.
- `L5Window.read_probe` runs `git fetch --quiet origin` in the repo root, then
  `git show`. Read-only for the working tree.
- The probe role is pinned to Haiku. The nonce proof depends on that small
  model following the wait-and-copy rule in `roles/probe.md`.
- `docs/ops/node-dispatch.md` (outside `touches`) still describes only the
  Windows wake fields; the POSIX `woke`/`why` are documented in
  `docs/ops/mesh-check.md`.

## Test totals

- Brief's list plus the new file: `1 failed, 464 passed in 15.91s` (the failure
  is item 2 above).
- Full suite, with the two deselects from the brief:
  `4 failed, 5276 passed, 33 skipped, 2 deselected in 451.69s (0:07:31)`.
  Failures:
  - `tests/test_w35_wire.py::test_on_posix_the_flag_changes_nothing_and_the_tmux_wake_is_the_one_used` (item 2)
  - `tests/test_w33_node_dispatch_windows.py::test_worker_letter_on_posix_goes_to_the_task_mailbox_and_wakes_its_tmux` (item 3)
  - `tests/test_ledger_direct_opens.py::test_step4b_gate_postgres_url_set_skips_local_file_check`
    and `tests/test_spawn_coo.py::test_send_shares_the_letter_for_coo_but_not_for_other_roles`:
    both also fail on an untouched export of the base commit (`fa8f57d9`,
    in the scratchpad). The first sees any in-flight task in the live hub
    (here, this one); the second raises `ArchivedDB`. Environmental, not caused
    by this diff.

## Skill learning

- MISSING [no owner]: the declared `touches` left out `tools/send_to_cxo.py`, `tests/test_w35_wire.py` and `tests/test_w33_node_dispatch_windows.py`, which the brief's own item 2 necessarily changes. A grep for the reply shape (`"delivered": True, "to"`) across tests/ finds them in seconds. · evidence: task-f9d23d0b
- MISSING [no owner]: `tests/test_w35_wake.py` hash-pins `attempt_wake`'s source; any change to that function needs the pin recomputed (sha256 of the LF-normalised source outside the W3.5 markers). · evidence: task-f9d23d0b, 60076e99
