---
name: dev-spawn-protocol
kind: protocol
description: MOVED to CXO_Protocol_DevSpawn on 2026-09-27. Read that skill; this stub is removed after 2026-10-27.
disable-model-invocation: true
created_by: agent
lifecycle: active
---

MOVED: this skill is now `CXO_Protocol_DevSpawn` (renamed 2026-09-27, docs/org/SKILL-KINDS-2026-09-27.md). Remove after 2026-10-27 or once no live file names it.
- 2026-09-28 [COSTLY] §2 Path lock — on an org-runtime task (`mooniex-agents`), `touches` is also the self_repo_guard allowlist (ADR 0020): a path under tools/, lib/, runners/, config/ or scripts/hook-* that is not in `touches` refuses the worker's Edit. I declared `tools/tmux.py` from memory (the file does not exist) and missed `tools/tmux_session.py`, so the worker stopped at its first edit. `ls` every guarded path before `create_task`; to extend later, update the row's `touches` in state/tasks.db and tell the worker (the guard re-reads it on every call) · evidence: task-5163bfca · status: pending
