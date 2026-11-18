# REPORT task-4983a577

## Summary

Completed the Org Mesh routing for Mac AGY conversations in `tools/send_to_agy.py` and added unit tests in `tests/test_node_dispatch_agy.py` and `tests/test_send_to_agy.py`, continuing from commits `ec4af77a` (`tools/node_dispatch.py`) and `c3e773c4` (`tools/send_to_agy.py`):

1. **`tools/node_dispatch.py` (from `ec4af77a`)**:
   - `verb_agy_list` (`agy_list`, 0 arguments in `_ARGSPEC`): read-only scan via `send_to_agy.scan_local_host(here, limit=50)` returning only `{box, uuid, cwd, last_activity, title, surface}` per conversation, with `title` collapsed to one line, secret-redacted via `_redact`, and capped at 90 chars (`AGY_TITLE_CHARS`). Language-server tokens (`csrf_token`, `ls_address`, `agentapi_exe`) and message bodies never enter the reply.
   - `_write_agy_letter` branch in `_write_letter`: when `to_role` is in `config.live_c_level_roles()` and `to_session` matches `AGY_SID_RE` (`agy-[0-9a-f]{8}`), verifies an existing, unparked `state/agy-sessions/<box>.json` record on the Mac whose `conversation_id` matches the `agy-<8 hex>` prefix (`_agy_record`), writes the letter to the Mac's `state/inbox/<box>/`, and wakes the conversation via `mail_wake.wake(box, label=from_role.upper())` (`handle_agy`). Refuses on Windows hosts (`_is_windows()`).

2. **`tools/send_to_agy.py`**:
   - Added `_host_ssh(host)`, `route_for(target_host, ...)`, `_normalize_remote_conversations(...)`, `_probe_mesh_host(host, limit=...)`, and `_deliver_mesh_letter(...)`.
   - `scan_host` (and `_probe_remote_host`) checks `_host_ssh(host) is None` (`mac.ssh` is `null`) and calls `_probe_mesh_host`, which dispatches `mesh.dispatch("mac", "agy_list")` and normalizes the returned rows.
   - `send` routes `mac` (`route == "mesh"`) through `_deliver_mesh_letter`: validates `<c-level>-agy-<8 hex>` box and safe sender tokens before touching the DB (returning `{"ok": False, "error": ...}` with zero DB writes on pre-check refusal), creates a `letters` row via `db.create_letter`, and calls `mesh.dispatch("mac", "deliver_letter", str(lid))`. On refusal (`ok: False`), `send_to_agy` returns `{"ok": False, "error": ...}` (and `main()` prints `send_to_agy error: ...` to `stderr` and exits `1`) without writing attempts or status changes to the DB.
   - `reply_to_claude` also routes `mac` (`route == "mesh"`) through `_deliver_mesh_letter` instead of dialling `ssh None`.
   - `contabo` local behavior and `winbox` SSH behavior remain unchanged.

3. **How the Mac-side session record (`state/agy-sessions/<box>.json`) gets to the Mac**:
   - An AGY conversation on the Mac registers its own `state/agy-sessions/<box>.json` via the AGY inbox hook (`scripts/hook-inbox.py`, which calls `agy_card_run.register_session` on each prompt) or manually on the Mac via `tools/agy_card_run.py register --session <box> --conversation <uuid>`.
   - `node_dispatch._agy_record` deliberately requires this pre-existing unparked record on the Mac and never creates one from a remote `deliver_letter` call, preventing a remote dispatch caller from arbitrarily registering and waking unopted-in local conversations in `accept-edits` mode.

## Files changed

- `tools/node_dispatch.py`
- `tools/send_to_agy.py`
- `tests/test_send_to_agy.py`
- `tests/test_node_dispatch_agy.py`
- `docs/reports/task-4983a577/REPORT.md`

## Outside-touches changes for CTO to apply at review

Per the CTO note in the task brief (`tests/test_w27_security.py` and `docs/ops/node-dispatch.md` are outside `touches`), here are the exact changes to apply at review:

### 1. `docs/ops/node-dispatch.md`

In `## Verbs` (around lines 11–24), add the `agy_list` row to the verb table:

```markdown
| `agy_list` | none | read-only: this host's AGY conversations (`tools.send_to_agy.scan_local_host`, capped at 50), one row each with `box`, `uuid`, `cwd`, `last_activity`, `title` (one line, ≤90 chars, secret-redacted) and `surface` (`App` or `CLI`) — never message bodies or language-server credentials, so `send_to_agy list` can read the Mac without an admin `ssh` alias |
```

And in the `deliver_letter` description or waking section, note that when `to_role` is a live C-level role and `to_session` matches `agy-[0-9a-f]{8}` on a POSIX host, `deliver_letter` checks for an existing unparked `state/agy-sessions/<role>-<sid>.json` record matching the UUID prefix, writes `state/inbox/<role>-<sid>/`, and calls `tools.mail_wake.wake`.

### 2. `tests/test_w27_security.py`

Without updating `tests/test_w27_security.py`, `_structured()` draws `"agy_list"` from `nd.HANDLERS`; when 0 args are picked (`raw = "agy_list"`), `nd.run_command("agy_list")` returns `(code=0, ok=True)` and `mesh.build_argv("contabo", "agy_list", ())` succeeds, whereas `_oracle("agy_list")` returns `None` (causing `test_fuzz_run_command_refuses_or_runs_exactly_the_allow_listed_call`, `test_fuzz_the_ssh_entry_prints_one_ascii_json_line`, and `test_fuzz_mesh_build_argv_sends_only_validated_plain_tokens` to fail). In addition, `test_fuzz_real_handlers_refuse_unknown_rows_before_any_backend` must skip `"agy_list"` alongside `"probe"`, `"kit"`, and `"start_clevel"` because `agy_list` is a read-only verb that does not look up a task or letter row.

```diff
diff --git a/tests/test_w27_security.py b/tests/test_w27_security.py
--- a/tests/test_w27_security.py
+++ b/tests/test_w27_security.py
@@ -151,6 +151,7 @@ _HEX8 = "[0-9a-f]{8}"
 _GRAMMAR = {
     "probe": (),
     "kit": (),
+    "agy_list": (),
     "pid_alive": (rf"task-{_HEX8}",),
     "spawn_worker": (rf"task-{_HEX8}",),
     "kill_worker": (rf"task-{_HEX8}",),
@@ -247,7 +248,7 @@ def _valid_command(rng: random.Random) -> str:
     hex8 = "".join(rng.choice("0123456789abcdef") for _ in range(8))
     roles = config_mod.live_c_level_roles()
     return rng.choice([
-        "probe", "kit",
+        "probe", "kit", "agy_list",
         f"pid_alive task-{hex8}", f"spawn_worker task-{hex8}", f"kill_worker task-{hex8}",
         f"publish_branch task-{hex8}", f"deliver_letter {rng.randint(0, 10 ** 12 - 1)}",
         f"start_clevel {rng.choice(roles)}",
@@ -370,7 +371,7 @@ def test_fuzz_real_handlers_refuse_unknown_rows_before_any_backend(wire):
     for i in range(2000):   # was 1500; three more verbs in the generator's pool dilute the hits
         raw = _hostile_command(rng, i)
         expect = _oracle(raw)
-        if expect is None or expect[0] in ("probe", "kit", "start_clevel"):
+        if expect is None or expect[0] in ("probe", "kit", "agy_list", "start_clevel"):
             continue  # probe, kit and start_clevel act without a row; covered above
         out, code = nd.run_command(raw)
         ran += 1
```

## Validation performed

- Added `tests/test_node_dispatch_agy.py` covering:
  - `agy_list` extra-argument and malformed-command refusals (`nd.run_command`, `nd.dispatch`, `mesh.build_argv`).
  - `verb_agy_list` strict 6-field output (`box`, `uuid`, `cwd`, `last_activity`, `title`, `surface`), omission of `csrf_token`/`ls_address`, title secret redaction and 90-char truncation.
  - W2.7 grammar parity check for `agy_list`.
  - `_write_agy_letter` via `deliver_letter`: registered unparked session delivery + `mail_wake.wake`, `woke: False` with redacted `why`, unregistered session refusal, parked session refusal, mismatched conversation UUID prefix refusal, Windows host refusal, and unsafe sender token refusal.
- Updated `tests/test_send_to_agy.py`:
  - Isolated `lib.db.DB_PATH` to `tmp_path / "tasks.db"` in an autouse fixture (ADR 0021).
  - Updated `test_list_conversations_scans_contabo_mac_winbox_with_ssh_mocked` to verify Mac is queried via `mesh.dispatch("mac", "agy_list")` while `winbox` uses `ssh winbox`.
  - Updated `test_send_remote_mac_and_winbox_resumes_over_ssh_with_host_map` to verify Mac sends create a `letters` row and call `mesh.dispatch("mac", "deliver_letter", str(lid))`, verify refused Mac deliveries return `ok: False` / exit `1` without writing attempts or status changes to the DB from `send_to_agy`, and keep `winbox` on `ssh winbox`.
  - Updated `test_reply_to_claude_from_contabo_mac_and_winbox` to verify replies aimed at `mac` also route through `mesh.dispatch("mac", "deliver_letter", str(lid))`.
- Per the AGY Remote Worker Contract (print-mode command allow-list prohibits invoking `python` directly from the worker shell), shell test execution (`python -m pytest tests/test_node_dispatch_agy.py tests/test_send_to_agy.py tests/test_w27_security.py`) is left to the review process.

## Not checked / risk

- **Pytest execution in review**: Because this worker ran under the AGY print-mode contract (where `python` is outside the shell allow-list), `pytest` was not executed in a subshell during this turn; please run `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_node_dispatch_agy.py tests/test_send_to_agy.py tests/test_w27_security.py` at review after applying the `tests/test_w27_security.py` diff above.
- **Unregistered Mac AGY conversations and watchdog retries**: When a Mac AGY conversation has never run `scripts/hook-inbox.py` or `tools/agy_card_run.py register` on the Mac, `verb_deliver_letter` on the Mac fails with `no registered, unparked AGY session <box> on this host` and calls `db.record_letter_attempt(lid, ...)` once (`attempts=1`, `status='pending'`). Because `lib/db.py` is outside `touches`, `send_to_agy` returns/prints the failure immediately without touching the DB row, and the hub watchdog will retry `deliver_letter` up to 4 more times (until `attempts` reaches 5 and `record_letter_attempt` flips `status='failed'`, or until the Mac conversation registers its session record and a retry delivers it).
- **Non-C-level AGY boxes on the Mac**: `node_dispatch._write_letter` routes `to_role in config.live_c_level_roles()` with `to_session` matching `agy-[0-9a-f]{8}` to `_write_agy_letter`. A Mac AGY conversation inferred under a worker or `project_head` box name (not `<c-level>-agy-<8 hex>`) is refused by `_deliver_mesh_letter` before `db.create_letter` is called.

## Blockers

- (none)

## Skill learning

- (none)
