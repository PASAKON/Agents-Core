# REPORT task-c2c24cbb

## Files changed

- tools/mesh_check.py: added live L9 on L5's pairs/waves, own-seat enforcement, cap skip, registration polling, first-turn letter, stop/resume validation and finally cleanup; stop failures fail the cell.
- tools/start_clevel_remote.py: added guarded importable JSON tool and CLI, atomic local rate reservations with an exclusive writer lock, mesh-enabled gate and best-effort sanitized audit events.
- lib/org_tools_registry.py: registered the async remote-start tool and its three parameters using the ask_run wrapper pattern.
- runners/cto_mcp_server.py: exposed the thin MCP wrapper with matching signature.
- scripts/test_org_tools_registry.py: added the tool to the expected registry names and updated the count in its verdict message.
- tests/test_mesh_check_l9.py: added lifecycle, cleanup, registration timeout, cap, own-seat, wave, live-gate and exit-code coverage with dispatch mocked.
- tests/test_start_clevel_remote.py: added guard, rolling rate-limit, corrupt-state, lock, audit and registry/MCP schema coverage with isolated state and SQLite audit rows.
- docs/design/org-mesh.md: documented L9, remote-start guards, budget/audit behavior, dispatch prerequisites and limitations.
- docs/reports/task-c2c24cbb/REPORT.md: recorded changes, validation and remaining acceptance work.

## Tests

Command run from the worktree root:

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_mesh_check_l9.py tests/test_start_clevel_remote.py tests/test_mesh_check.py -o addopts="" -p no:warnings
```

Completed verdict: `1 failed, 192 passed in 19.15s`. Failure:
`tests/test_mesh_check.py::test_amain_live_exits_0_when_everything_claimed_is_green_or_closed`.
Its existing `_stub_levels` mocks SEC/L5/L6/L7 but not the newly added L9.
The real L9 correctly fails because `ORG_MESH_DISPATCH` is disabled. The
test file is outside the edit allow-list, so it was not changed.

After adding independent integration coverage for the live gate and L9 exit code:

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_mesh_check_l9.py tests/test_start_clevel_remote.py -o addopts="" -p no:warnings
```

Final new-test verdict: `30 passed in 2.91s` (12 L9, 18 remote-start).

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python scripts/test_org_tools_registry.py
```

Exit 0; own verdict line: `ALL PASS`. Registry shape line:
`[PASS] registry has exactly the 26 cto_mcp_server.py tool names`.

`git diff --check`: passed.

An earlier combined run and an isolated diagnostic run of
`tests/test_start_clevel_remote.py::test_registry_and_mcp` (with
`-o faulthandler_timeout=15`) were interrupted without pytest totals after
the event loop stalled awaiting a thread-pool wakeup in the sandbox. The
wiring test now replaces `asyncio.to_thread` with an inline async adapter;
production retains the ask_run-style thread wrapper. The completed runs above
used that isolated test adapter.

## Not verified

- No live mesh, SSH, service or session operations were performed. Mac, winbox and Contabo must run `mesh_check --expect <wave> --live` from their own seats with dispatch enabled and keys deployed; paste that output into the issue.
- The parallel node_dispatch probe/start/resume/stop verbs are a dependency and were mocked, not edited or exercised here. Live registration, first-turn transcript creation, resume UUID preservation, cross-host resume refusal and cleanup require deployed launchers and the hub.
- L9 does not compare transcripts; it relies on the remote verb refusing resume without a resumable UUID. A start whose response is lost cannot expose its session id for caller cleanup.
- Concurrent session starts can race the hub cap precheck; launcher-side cap enforcement remains necessary. A process killed during a rate reservation may leave a lock file; it fails closed until removed after confirming no writer remains.

## Blockers

- The existing mesh-check suite needs one fixture update outside the allowed paths: add an L9 stub alongside L5 in `tests/test_mesh_check.py::_stub_levels`. This is required for its all-green integration test to model the new level. No out-of-scope file was edited to hide the failure.
- Live acceptance cannot be completed under the explicit no-network/no-session-operation contract and depends on the parallel remote-verb task deployment.

## Skill learning

- (none)
