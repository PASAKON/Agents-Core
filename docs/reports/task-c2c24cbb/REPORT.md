# REPORT task-c2c24cbb

## Files changed

Round 2 restored round 1 from fetched `origin/agent/codex-task-c2c24cbb` (commit `eafe84ad`). The supplied `origin/agent/codex-task-task-c2c24cbb` ref does not exist locally; the matching task branch contains the reviewed implementation. No git metadata was changed.

- tools/mesh_check.py: restored live L9 lifecycle, cap skip and cleanup; moved L9 EXPECT.update immediately after EXPECT without behavior changes.
- tools/start_clevel_remote.py: restored guarded remote-start tool; reclaim locks older than 60 seconds and retry exclusive creation once; return unreachable details redacted when the helper is importable and limited to 200 characters, retaining only the exception class as the audit outcome.
- lib/org_tools_registry.py: restored remote-start registration and async wrapper.
- runners/cto_mcp_server.py: restored remote-start MCP wrapper.
- scripts/test_org_tools_registry.py: restored remote-start name in expected registry tools.
- tests/test_mesh_check_l9.py: restored lifecycle, cleanup, cap, own-seat and integration coverage.
- tests/test_start_clevel_remote.py: restored guard/rate/audit/wiring coverage; added stale-lock takeover, fresh/boundary lock refusal, redacted/unavailable-redactor unreachable details and audit exclusion assertions.
- docs/design/org-mesh.md: restored L9 and remote-start usage, guards, prerequisites and limitations.
- docs/reports/task-c2c24cbb/REPORT.md: replaced round 1 report with round 2 evidence.

## Tests

Exact command from the worktree root:

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_mesh_check_l9.py tests/test_start_clevel_remote.py tests/test_mesh_check.py -o addopts="" -p no:warnings
```

Pytest verdict: `1 failed, 198 passed in 26.99s` (199 collected).
Breakdown: L9 12 passed; remote-start 21 passed; existing mesh-check 165 passed, 1 failed.
The failure remains `tests/test_mesh_check.py::test_amain_live_exits_0_when_everything_claimed_is_green_or_closed`: `_stub_levels` does not stub L9, so the real L9 fails with `ORG_MESH_DISPATCH is disabled`. That test file is outside the permitted edit list and was not modified.

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python scripts/test_org_tools_registry.py
```

Exit 0. Exact verdict line: `ALL PASS`.
Registry shape: `[PASS] registry has exactly the 26 cto_mcp_server.py tool names`.

`git diff --check`: passed.

## Not verified

- No live mesh, SSH, service or session operations were performed. Mac, winbox and Contabo must run live acceptance from their own seats with ORG_MESH_DISPATCH and dispatch keys configured.
- Dispatch is mocked: hub registration, transcript creation, resume UUID preservation, remote refusal and cleanup still require deployed launchers and a live hub. L9 does not compare transcripts.
- A lost start response cannot provide a session ID for cleanup; concurrent starts still rely on launcher-side cap enforcement.

## Blockers

- The existing all-green mesh-check integration fixture requires an L9 stub in `tests/test_mesh_check.py::_stub_levels`, outside the edit allow-list. This remains the only requested-suite failure.
- Live acceptance is outside the no-network/no-session-operation contract and remains for the CTO/deployed hosts.

## Skill learning

- (none)
