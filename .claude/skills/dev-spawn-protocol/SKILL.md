---
name: dev-spawn-protocol
kind: protocol
description: MOVED to CXO_Protocol_DevSpawn on 2026-09-27. Read that skill; this stub is removed after 2026-10-27.
disable-model-invocation: true
created_by: agent
lifecycle: active
---

MOVED: this skill is now `CXO_Protocol_DevSpawn` (renamed 2026-09-27, docs/org/SKILL-KINDS-2026-09-27.md). Remove after 2026-10-27 or once no live file names it.
- 2026-09-28 [MISSING] §remote — delegating FROM a non-Mac host is not wired: on Contabo `delegate_task(host=None)` resolves to 'mac' and hits Mac paths (tools/worktree.py FileNotFoundError), and `host='contabo'` ssh's to itself through an alias Contabo does not have (`Could not resolve hostname mooniex-vps`); `merge_task` also needs the Mac path, so Contabo→winbox work is merged by hand. Until org-mesh W0 lands, a Contabo session uses `host='winbox'` + hand merge, or the in-session Agent tool · evidence: task-cf5db03d (Contabo ledger, 2026-09-28 01:50), task-854cb512, docs/design/org-mesh.md §1c · status: pending
