# Permission Matrix

Source of truth: `Agents/policies/agents.yaml`. This page is human-readable mirror.
If they diverge, code wins (gates are enforced by `lib/config.is_c_level` +
tool-level checks in `Agents/tools/*`).

## Roles

| Role          | Level | Model              | Wiki Write | Create Task | Merge | Push | Delete Branch | Workspace Only |
|---------------|-------|--------------------|:----------:|:-----------:|:-----:|:----:|:-------------:|:--------------:|
| ceo           | C     | (human)            | yes        | yes         | yes   | yes  | yes           | no             |
| cto           | C     | claude-opus-4-7    | yes        | yes         | yes   | yes  | yes           | no             |
| frontend_dev  | W     | claude-sonnet-4-6  | no         | no          | no    | no   | no            | yes            |
| backend_dev   | W     | claude-sonnet-4-6  | no         | no          | no    | no   | no            | yes            |
| devops        | W     | claude-sonnet-4-6  | no         | no          | no    | no   | no            | yes            |
| qa            | W     | claude-haiku-4-5   | no         | no          | no    | no   | no            | yes            |

Level: C = C-level, W = Worker.

## Tool → Role Allow

| Tool                | CTO | DEV | QA  |
|---------------------|:---:|:---:|:---:|
| `wiki_read`         | yes | yes | yes |
| `wiki_list`         | yes | yes | yes |
| `wiki_search`       | yes | yes | yes |
| `wiki_write`        | yes | no  | no  |
| `create_task`       | yes | no  | no  |
| `delegate_task`     | yes | no  | no  |
| `delegate_parallel` | yes | no  | no  |
| `get_task`          | yes | yes | yes |
| `review_diff`       | yes | no  | no  |
| `merge_task`        | yes | no  | no  |
| `reopen_task`       | yes | no  | no  |
| `Read` / `Glob` / `Grep` | yes (anywhere) | yes (cwd=worktree) | yes (cwd=worktree) |
| `Write` / `Edit` / `Bash` | yes (anywhere) | yes (cwd=worktree) | yes (cwd=worktree) |

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
