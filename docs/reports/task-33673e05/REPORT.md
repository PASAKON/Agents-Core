# REPORT task-33673e05

## Files changed
- conftest.py: disable mesh probing by default in an autouse fixture to prevent live dispatch and alerts during tests.
- runners/watchdog.py: require mesh.enabled() for probing and name all skip conditions in the once-only log.
- tests/test_watchdog_mesh_probe.py: enable mocked mesh dispatch, cover mesh-off skips, forced calls, CLI exit 2, and enabled state writes; capture and assert the root default before the local fixture opts in. Every probe test keeps MESH_PROBE_STATE under tmp_path; no monkeypatch.undo() is used.
- docs/ops/node-dispatch.md: document the mesh dispatch gate and root test off-switch.
- docs/reports/task-33673e05/REPORT.md: record changes, validation and limitations.

## Tests
Exact commands and printed totals:

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_watchdog_mesh_probe.py -o addopts="" -p no:warnings
```
34 passed in 0.74s.

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w04_self_host_sites.py tests/test_w15_duty_split.py tests/test_w23_mesh_dispatch.py tests/test_w24_letters.py tests/test_w42_provision.py -o addopts="" -p no:warnings
```
Collected 380 items; interrupted (exit 130) after several minutes without progress in test_w23_mesh_dispatch.py. No final pass/fail totals printed.

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w04_self_host_sites.py tests/test_w15_duty_split.py -o addopts="" -p no:warnings
```
133 passed in 31.52s.

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w24_letters.py tests/test_w42_provision.py -o addopts="" -p no:warnings
```
100 passed, 66 skipped in 40.68s.

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w23_mesh_dispatch.py -o addopts="" -p no:warnings -o faulthandler_timeout=30 -v
```
Collected 81 items; diagnostic stack showed test_flag_on_remote_spawn_is_one_spawn_worker_through_mesh blocked in _spawn (line 129), asyncio.run(delegate._spawn_remote(...)), with the main thread in selectors.select and an executor worker waiting. Interrupted (exit 130); no final pass/fail totals printed. No changes made to that test or delegate code.

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w23_mesh_dispatch.py -k scan_once -o addopts="" -p no:warnings
```
1 passed, 80 deselected in 0.79s.

`git status --short state/`: no output after testing.
`git diff --check`: passed.

## Not verified
- Live Mac/winbox dispatch, alert delivery and running watchdog services were not exercised; probe tests use fakes.
- Full test_w23_mesh_dispatch.py completion is unverified because of the async spawn hang above. Its scan_once caller passed separately.
- The known failing scripts/test_watchdog_reap.py and scripts/test_surface_reaper.py suites were not run, as instructed.

## Blockers
- Full requested caller-suite validation is blocked by the reproducible async spawn hang in test_w23_mesh_dispatch.py. Investigating or editing its spawn implementation is outside the permitted change scope; review should rerun that file in its environment.

## Skill learning
- (none)
