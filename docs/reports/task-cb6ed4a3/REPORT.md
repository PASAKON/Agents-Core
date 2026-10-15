# REPORT task-cb6ed4a3

Summary: identity resolution: fail closed.

## Callers found (`file:line`)

### `current_identity`, `CEO_IDENTITY`, and `_resolve_sender_role`
- `tools/agent_transport.py:88` — `_resolve_sender_role()`: resolves sender display label from process environment.
- `tools/agent_transport.py:120` — `CEO_IDENTITY = Identity("ceo", "CEO", None)`: constant for the root CEO identity.
- `tools/agent_transport.py:123` — `current_identity()`: resolves caller `Identity` from process environment.
- `tools/send_to_cxo.py:90-96` — imports `CEO_IDENTITY`, `Identity`, `_resolve_sender_role`, `current_identity` from `tools.agent_transport`.
- `tools/send_to_cxo.py:601-603` — `spawn()`: calls `current_identity()`, `authorize()`, and `_sender_label()`.
- `tools/send_to_cxo.py:833-835` — `send()`: calls `current_identity()`, `authorize()`, and `_sender_label()`.
- `tools/send_to_cxo.py:867-885` — `_sender_label()`: calls `_resolve_sender_role()`.
- `tools/send_to_cxo.py:881` — `_ph_owner_session()`: calls `current_identity()`.
- `tools/send_to_cxo.py:897-899` — `_send_to_ph()`: calls `current_identity()`, `authorize()`, and `_sender_label()`.
- `tools/send_to_worker.py:83-87` — imports `_resolve_sender_role`, `current_identity` from `tools.agent_transport`.
- `tools/send_to_worker.py:311-312` — `send()`: calls `current_identity()` and `_resolve_sender_role()`.
- `tools/spawn_ph.py:104-110` — `_caller()`: imports and calls `current_identity()`, catching `PermissionError`.
- `tools/spawn_ph.py:326,340` — `spawn()`: imports `Identity` to record spawn ownership via `send_to_cxo.record_spawn()`.
- `lib/ceo_report.py:44,347` — `report_to_ceo()`: imports and calls `current_identity()` to verify the caller is a C-level session.

### Console / Secretary / SomPong / MCP / daemon paths calling `send_to_cxo`, `send_to_worker`, `send_to_cto`
- `runners/relay_mcp_server.py:107,930-989` — `relay_to_session()`: constructs `Identity("secretary", SECRETARY_FROM_ROLE, SECRETARY_FROM_SESSION_ID)` (`Identity("secretary", "secretary", "sompong")`) directly and passes it to `authorize()` and `mailbox.send()`; does not call `current_identity()`.
- `runners/mac_agent.py:66,397-431` — `do_relay()`: constructs `Identity("secretary", SECRETARY_FROM_ROLE, SECRETARY_FROM_SESSION_ID)` directly and passes it to `authorize()` and `mailbox.send()`; does not call `current_identity()`.
- `scripts/cxo-claude.sh:350-388,818` — C-level, Project Head, and SomPong (`--role coo`) launcher: sets `CXO_ROLE`, `CXO_SESSION=1`, and `CXO_SESSION_ID` (plus `CTO_SESSION=1` and `CTO_SESSION_ID` when `role=cto`).
- `scripts/cto-claude.sh:90-112` — CTO launcher: sets `CTO_SESSION=1` and `CTO_SESSION_ID`.
- `lib/org_tools_registry.py:424` — `do_send_to_worker()` MCP tool handler (runs inside C-level MCP server with `CXO_ROLE`/`CTO_SESSION_ID` set).
- `lib/org_tools_registry.py:441` — `do_send_to_cto()` MCP tool handler (runs inside worker MCP server with `WORKER_TASK_ID`/`WORKER_ROLE` set).
- `lib/org_tools_registry.py:459` — `do_send_to_cxo()` MCP tool handler (runs inside C-level/PH/worker MCP server).
- `tools/delegate.py:731,876,1347,2416` — calls `send_to_worker.send()` and `send_to_cto.send()` during task delegation/resume.
- `tools/send_to_cto.py:60,179` — `send()`: takes explicit `from_id` and `role` arguments and uses `agent_transport._active_session_id()`; does not call `current_identity()`.
- `runners/watchdog.py:290` — `_send_ping()`: invokes `python -m tools.send_to_worker <task_id> <message>` as a subprocess (updated to set `CTO_SESSION_ID=watchdog` when no C-level session env is present).
- `runners/watchdog.py:303` — `_notify_cto()`: invokes `python -m tools.send_to_cto` with explicit `--from` and `--role`.

## Marker chosen and fail-closed resolution

- **Marker**: `CEO_SESSION=1` (constant `CEO_SESSION_ENV = "CEO_SESSION"` in `tools/agent_transport.py`; `ORG_CEO_SESSION=1` is also accepted by `_has_ceo_marker()`).
- **Who sets what**:
  - Direct CEO CLI invocations (`python -m tools.send_to_cxo`, `python -m tools.send_to_worker`) require `CEO_SESSION=1` in the caller's environment to resolve as `CEO_IDENTITY` / `"CEO"`.
  - Console / Secretary relay calls (`runners/relay_mcp_server.py::relay_to_session`, `runners/mac_agent.py::do_relay`) authenticate with `Identity("secretary", "secretary", "sompong")` directly.
  - C-level and Project Head launchers (`scripts/cto-claude.sh`, `scripts/cxo-claude.sh`) `unset CEO_SESSION ORG_CEO_SESSION` and export `CTO_SESSION_ID` / `CXO_ROLE` + `CXO_SESSION_ID`.
  - Worker launcher (`runners/worker_init.py`) strips `CEO_SESSION`, `ORG_CEO_SESSION`, `CXO_ROLE`, `CXO_SESSION`, `CXO_SESSION_ID`, `CTO_SESSION`, `CTO_SESSION_ID`, and `ORG_PH_*` before exporting `WORKER_TASK_ID` and `WORKER_ROLE`.
  - Watchdog (`runners/watchdog.py::_send_ping`) sets `CTO_SESSION_ID=watchdog` in the subprocess environment when invoking `tools.send_to_worker`.
- **Precedence and non-escalation**:
  - `current_identity()` and `_resolve_sender_role()` evaluate `WORKER_TASK_ID` first, then `CXO_ROLE` (live C-level roles and `project_head`), then `CTO_SESSION_ID`, and only check `_has_ceo_marker()` when none of `_NON_CEO_IDENTITY_ENVS` (`WORKER_TASK_ID`, `WORKER_ROLE`, `CXO_ROLE`, `CXO_SESSION_ID`, `CXO_SESSION`, `CTO_SESSION_ID`, `CTO_SESSION`, `ORG_PH_LANE`, `ORG_PH_PROJECT`, `ORG_PH_OWNER`) are set.
  - A bare or partial environment raises `PermissionError`.

## Files changed

- `tools/agent_transport.py`: make `_resolve_sender_role()` and `current_identity()` fail closed with `PermissionError` when no recognised identity is present; add `CEO_SESSION_ENV = "CEO_SESSION"` and `_has_ceo_marker()` with strict precedence behind worker, C-level, and Project Head identities.
- `tools/send_to_cxo.py`: re-export `CEO_SESSION_ENV`; fall back to the resolved `Identity` role in `_sender_label()` when `current_identity` is monkeypatched in unit tests on a bare environment.
- `tools/send_to_worker.py`: re-export `CEO_SESSION_ENV`; catch `PermissionError` in `main()` and exit with status 4.
- `lib/ceo_report.py`: catch `PermissionError` from `current_identity()` in `report_to_ceo()` and return a `"rejected: ..."` string.
- `runners/watchdog.py`: pass `CTO_SESSION_ID=watchdog` in `_send_ping()` subprocess environment when unset.
- `runners/worker_init.py`: strip `CEO_SESSION`, `ORG_CEO_SESSION`, `CXO_*`, `CTO_*`, and `ORG_PH_*` from the worker environment.
- `scripts/cto-claude.sh`: `unset CEO_SESSION ORG_CEO_SESSION`.
- `scripts/cxo-claude.sh`: `unset CEO_SESSION ORG_CEO_SESSION`.
- `tests/test_identity_fail_closed.py`: new pytest suite covering bare-env refusal, CEO paths (`CEO_SESSION=1` and secretary relay), worker/C-level/PH resolution, and non-escalation when `CEO_SESSION=1` is set inside a worker/C-level/PH env.
- `tests/test_wake_screen_gate.py`, `scripts/test_cxo_crosstalk.py`, `scripts/test_mailbox.py`, `scripts/test_send_to_worker.py`: set `CEO_SESSION=1` in fixtures/tests that exercise CEO sends.

## Validation and what could not be verified

Per the AGY remote worker contract ("For AGY, use file tools only; leave shell validation to the review process"), `pytest` was not executed from a shell during this run. Run the following command from the worktree root to verify:

```
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_identity_fail_closed.py tests/test_wake_screen_gate.py scripts/test_cxo_crosstalk.py scripts/test_mailbox.py scripts/test_send_to_worker.py
```

## Blockers

- (none)

## Skill learning

- (none)
