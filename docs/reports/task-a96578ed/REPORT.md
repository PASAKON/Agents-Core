# REPORT task-a96578ed

## Changes
- Restored the reviewed round-2 baseline (e4b26d53), including round-1 kit path forwarding. The assigned worktree initially pointed at b422bcde instead.
- tools/mesh_check.py: renamed memory_hook to memory_pull; inspect the platform PH launcher for a tools.memory_sync pull module call, ignoring comment lines. Check core/tools/memory_sync.py independently. Keep deadline SessionStart checks unchanged. Rename the compact table column.
- tests/test_mesh_check_kit.py: fixtures now put memory pull in launchers; cover both platforms, missing launchers, comments, wrong commands, independent script checks, and rejection of a hook-only memory pull.
- docs/ops/mesh-check.md: document launcher memory pull and separate script fact.
- config/hosts.yaml: restored only the reviewed core path addition; no IP addresses added or changed.

## Validation
- Core's existing virtualenv: python -m pytest -q tests/test_mesh_check*.py — 264 passed, exit 0 (264 confirmed by collection).
- Additional table-header assertion: test_wave_and_render — 1 passed.
- git diff --check — passed.
- gitleaks 8.30.1 on the diff, with redaction — no leaks found.
- No SSH, network probes, fetches, settings edits, or hook execution performed. Tests use local fixtures.

## Blockers
- Git metadata is mounted read-only outside the permitted worktree. Fast-forwarding to the reviewed commit failed creating ORIG_HEAD.lock. Restored reviewed content using apply_patch instead. Cannot create the requested commit here; launcher must retain the reviewed history, commit the correction/report, push, and open the PR as directed.
- Current HEAD remains b422bcdefe8ca757c77c9de32f013dbd93a62758; no new commit SHA or PR number is available in this worker.
- System Python has no pytest; validation used /opt/MoonieXHQ/Agents/Core/.venv/bin/python.

## Skill learning
- (none)
