# Task task-77ec5adc

Project: Mooniex Agents (meta-repo) (mooniex-agents)
Stack: python
Repo path (your worktree, work ONLY here): /Users/gob/Projects/Agents/worktrees/mooniex-agents__developer__task-77ec5adc
Branch: agent/developer-task-77ec5adc
Default branch (do NOT touch): main

## Description

## Scope (Phase 1 only — additive, low risk)

Implement the **safety helpers** from the new playbook + ADR:
- Playbook: `LLMs/playbooks/cxo-tab-lifecycle.md`
- ADR: `LLMs/decisions/2026-05-26-cxo-tab-id-locked-close.md`

This Phase 1 task is **additive only**. Do NOT change `tools/send_to_cxo.py` or `scripts/cxo-claude.sh` behavior. Phase 2 (ephemeral-spawn pattern + initial-prompt flag) is a separate task.

## Deliverables

### 1. `scripts/cleanup-zombies.sh` (new)

Bash script that scans `state/locks/*.winid` files and deletes ones whose winid is not in iTerm's live `id of windows` list. **Never closes a live tab.** File-only GC.

```bash
#!/usr/bin/env bash
# scripts/cleanup-zombies.sh — remove stale *.winid lock files only.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKS="$ROOT/state/locks"
live="$(osascript -e 'tell application "iTerm2" to return id of windows' | tr -d ' ')"
removed=0
for f in "$LOCKS"/*.winid; do
  [ -e "$f" ] || continue
  wid="$(cat "$f")"
  case ",$live," in
    *",$wid,"*) ;;
    *) rm -f "$f"; removed=$((removed+1));;
  esac
done
echo "cleanup-zombies: removed $removed stale lock file(s)"
```

Make executable: `chmod +x scripts/cleanup-zombies.sh`.

### 2. `tools/itermtab.py` — strengthen `close_session`

Extend the existing `close_tab(task_id)` helper or add a new `close_session(role: str, session_id: str) -> bool` function with the safety gates from the playbook:

1. `state/locks/<role>-<session_id>.winid` must exist
2. Its winid must be in iTerm's live window list
3. The caller's `os.environ.get("CXO_ROLE")` must equal `role` AND `os.environ.get("CXO_SESSION_ID")` must equal `session_id` (caller-identity check)
4. Query `state/agents.db` — no task with this `session_id` may have `status='in_progress'` (consult existing `lib/db.py` for the right query; if no such linkage column exists, log a TODO and proceed without the DB check for Phase 1 — do NOT add a schema migration in this task)

If any of (1)-(3) fails, log to `state/locks/close-refusals.log` (append, one JSON line per refusal: `{ts, role, session_id, reason}`) and return `False`. Never raise.

Add type hints + a 3-line docstring at the function head. Keep code minimal.

### 3. `runners/cto.py` — boot hook

On CTO startup, call `scripts/cleanup-zombies.sh` (subprocess, non-blocking, ignore failures). Add it near where the existing session-lock file is written. One call, no retry loop. Log the script's stdout line via the existing logger.

## Acceptance

- [ ] `bash scripts/cleanup-zombies.sh` removes only stale lock files; running with no zombies prints `removed 0 stale lock file(s)`
- [ ] `close_session("cto", "fakesession")` returns False + writes refusal log
- [ ] `close_session(role, sid)` succeeds only when env + lock + live-winid all match
- [ ] CTO startup invokes cleanup once, log line visible
- [ ] No change to `send_to_cxo.py`, `cxo-claude.sh`, or `cto-claude.sh` behavior
- [ ] `pytest -q` passes (existing suite); add a unit test for `close_session` refusal path

## Out of scope (Phase 2 — separate task)

- `send_to_cxo.py` `--spawn` flag + ephemeral-spawn default
- `cxo-claude.sh --initial-prompt`
- Idle-ping daemon
- DB schema migration for `c_level_sessions.active_task_id`

## Reviewer

CTO. Merge after Phase 1 acceptance passes.

---

## Instructions

1. Read your role doc (already in your system prompt).
2. Read relevant wiki pages (use mcp__org__wiki_read).
3. Inspect the codebase you've been given (your cwd is the worktree).
4. Implement the task incrementally with commits inside your worktree.
5. Run tests if patterns exist.
6. When done, call `mcp__org__submit_report` with your final report
   (files changed, tests run, blockers). This is how the CTO learns
   you finished — without it the task stays in_progress forever.

Begin.
