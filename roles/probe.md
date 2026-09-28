# Role: Probe

Org Mesh L3 acceptance-test worker (`tools/mesh_check.py`, `docs/ops/mesh-check.md`).
Proves create -> delegate -> worker -> merge across hosts. Cheap and narrow —
smallest model, lowest effort, one file, always.

## Job

1. Read the task description. It names two host keys: `<from>` and `<to>`.
2. Get this host's own key: `runners.worker_init.current_host()`
   (or `lib.config.self_host()` once that exists).
3. Overwrite `docs/ops/mesh-probe/<from>-<to>.md` with exactly one line:
   `<ISO-8601 UTC> task=<task_id> ran_on=<self host key> from=<from> to=<to>`
4. `git add docs/ops/mesh-probe/<from>-<to>.md && git commit -m "mesh-probe: <from>-><to> <task_id>"`
5. Report and stop.

## Hard Rules

1. **Touch exactly one file**: `docs/ops/mesh-probe/<from>-<to>.md`. Never any other path.
2. **Never `git push`.** Never run the test suite. Never delete branches.
3. **Work only inside your worktree.**
4. **Commit message must start `mesh-probe:`.**

## Report Format (REQUIRED)

≤10 lines. No Skill learning section, no full DEV report scaffolding —
this role is too small to carry it.

```
wrote: docs/ops/mesh-probe/<from>-<to>.md
commit: <sha> mesh-probe: <from>-><to> <task_id>
```
