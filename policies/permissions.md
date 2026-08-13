# Permission Matrix

Source of truth: `Agents/policies/agents.yaml`. This page is human-readable mirror.
If they diverge, code wins (gates are enforced by `lib/config.is_c_level` +
tool-level checks in `Agents/tools/*`).

## Roles

Mirrors `config.agents()` as of 2026-08-13. The previous table listed
`frontend_dev` / `backend_dev` / `devops` / `qa` — none of which have
existed since the role set was rebuilt around deliverable kind rather than
job title — and pinned models two generations out of date.

| Role                | Level | Model             | Wiki Write | Create Task | Merge | Push | Delete Branch | Workspace Only |
|---------------------|-------|-------------------|:----------:|:-----------:|:-----:|:----:|:-------------:|:--------------:|
| ceo                 | C     | (human)           | yes        | yes         | yes   | yes  | yes           | no             |
| cto                 | C     | claude-sonnet-5   | yes        | yes         | yes   | yes  | yes           | no             |
| cfo                 | C     | claude-sonnet-5   | yes        | yes         | yes   | yes  | yes           | no             |
| cgo                 | C     | claude-sonnet-5   | yes        | yes         | yes   | yes  | yes           | no             |
| cmo                 | C     | claude-sonnet-5   | yes        | yes         | yes   | yes  | yes           | no             |
| developer           | W     | claude-sonnet-5   | no         | no          | no    | no   | no            | yes            |
| tester              | W     | claude-sonnet-5   | no         | no          | no    | no   | no            | yes            |
| web_designer        | W     | claude-sonnet-5   | no         | no          | no    | no   | no            | yes            |
| browser_operator    | W     | claude-sonnet-5   | no         | no          | no    | no   | no            | yes            |
| video_editor        | W     | claude-sonnet-5   | no         | no          | no    | no   | no            | yes            |
| devops_engineer     | W     | claude-opus-5     | no         | no          | no    | no   | no            | yes            |
| security_engineer   | W     | claude-opus-5     | no         | no          | no    | no   | no            | yes            |
| data_analyst        | W     | claude-sonnet-5   | no         | no          | no    | no   | no            | yes            |
| prompt_engineer     | W     | claude-sonnet-5   | no         | no          | no    | no   | no            | yes            |
| ads_manager         | W     | claude-sonnet-5   | no         | no          | no    | no   | no            | yes            |
| content_strategist  | W     | claude-sonnet-5   | no         | no          | no    | no   | no            | yes            |
| script_writer       | W     | claude-sonnet-5   | no         | no          | no    | no   | no            | yes            |

Level: C = C-level (`config.agents()["c_level"]`), W = Worker.

`devops_engineer` and `security_engineer` sit on Opus because a cheap miss
in deploy-adjacent or secrets-adjacent work is expensive — see
`decisions/0009-model-routing-policy.md`. Per-task overrides live in
`tasks.model_hint`, and `lib/quota_router.py` may route a worker to GLM-5.2
when `DEV_MODEL_PROVIDER=auto` and Claude quota is short.

## Tool → Role Allow

A worker's entire tool surface is the seven rows marked yes below —
enumerated by `runners/dev_mcp_server.py`, not by this prose. There is no
partially-privileged worker tier: every W role above gets exactly this set.

| Tool                     | C-level | Worker |
|--------------------------|:-------:|:------:|
| `wiki_read`              | yes     | yes    |
| `wiki_list`              | yes     | yes    |
| `wiki_search`            | yes     | yes    |
| `submit_report`          | no      | yes    |
| `file_blocker_issue`     | no      | yes    |
| `request_human_handoff`  | no      | yes    |
| `dev_message`            | no      | yes    |
| `wiki_write`             | yes     | no     |
| `create_task`            | yes     | no     |
| `check_collisions`       | yes     | no     |
| `delegate_task`          | yes     | no     |
| `delegate_parallel`      | yes     | no     |
| `get_task`               | yes     | no     |
| `review_diff`            | yes     | no     |
| `merge_task`             | yes     | no     |
| `reopen_task`            | yes     | no     |
| `close_dev`              | yes     | no     |
| `Read` / `Glob` / `Grep` | yes (anywhere) | yes (cwd=worktree) |
| `Write` / `Edit` / `Bash`| yes (anywhere) | yes (cwd=worktree) |

## Enforcement Layers

1. **Code gate** — `wiki_write` checks `is_c_level(role)` before writing.
2. **Tool registration** — DEV runners only register read-only tools (`Agents/runners/dev.py` line ~37).
3. **`cwd` lock** — DEV subprocess gets `cwd=worktree`. Reads/writes outside need explicit absolute paths (still possible via Bash — see below).
4. **Branch ownership** — DEV branches named `agent/<role>-<task_id>`. Main branch never checked out by DEV.

## Known Gaps

- DEV can technically run `git push` via Bash tool if they construct the command.
  Defense: pre-tool hook in `Agents/tools/` that blocks `git push` outside CTO.
  *(Not yet implemented — Phase 2.)*
- DEV can `cd` outside cwd via Bash. Currently relies on system prompt discipline.
  Defense: process-level chroot or container.
  *(Not yet implemented.)*

## Adding a Permission

1. Add field to `agents.yaml` (e.g. `can_view_secrets: true`).
2. Add check in relevant tool: `if not role_cfg["can_view_secrets"]: raise PermissionError(...)`.
3. Update this matrix.
4. Update `Agents/README.md` "How to Add a Role" if structure changes.
