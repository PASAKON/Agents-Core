# REPORT task-6c9b372a

## Summary

Allowed mesh AGY letter delivery in `tools/send_to_agy.py` (`_deliver_mesh_letter`) to target `project_head-agy-<8 hex>` boxes in addition to live C-level `agy-<8 hex>` boxes, while keeping the fullmatch check `_MESH_AGY_SID_RE` (`agy-[0-9a-f]{8}`) unchanged and rejecting free-form session IDs or any other roles.

## Files changed

- `tools/send_to_agy.py`:
  - Updated `_deliver_mesh_letter` (`require_agy_box=True` guard) to accept `to_role == "project_head"` alongside `org_config.live_c_level_roles()`, keeping `_MESH_AGY_SID_RE.fullmatch(to_sid)` intact.
  - Updated the refusal message to `"refused: mesh AGY delivery to {target_host} requires a <c-level|project_head>-agy-<8 hex> box, got {to_role}-{to_sid}"`.
- `tests/test_send_to_agy.py`:
  - Added `test_deliver_mesh_letter_allows_c_level_and_project_head_agy_boxes_only` covering:
    - `project_head` + `agy-1a2b3c4d` passes the guard
    - `project_head` + `bl-autoqueue` is still refused
    - `cgo` + `agy-89abcdef` still passes
    - `random_role` + `agy-1a2b3c4d` is still refused

## Validation performed

- Inspected `tools/send_to_agy.py` and `tests/test_send_to_agy.py` via file tools per the AGY Remote Worker Contract (file tools only; shell validation left to the review process).

## Not checked / risk

- Per the AGY Remote Worker Contract ("For AGY, use file tools only; leave shell validation to the review process"), `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_send_to_agy.py` was not executed in a shell during this headless AGY run and should be run by the reviewer.
- End-to-end live mesh dispatch to the Mac `project_head-agy-<8 hex>` box depends on the recipient side (`node_dispatch.py` / `mail_wake.py`) already supporting `project_head-agy-<8 hex>` session records in `state/agy-sessions/`.

## Blockers

- (none)

## Skill learning

- (none)
