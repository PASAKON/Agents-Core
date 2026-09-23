# Model fallback — which model runs where, and what happens when one is out

Updated 2026-09-23 (Z.ai and 9Router retired by the CEO on 2026-09-20; no proxy anywhere).

- **C-levels (CTO/CFO/CGO/CMO)** run on Claude credit: `claude-opus-5-5[1m]` at effort xhigh,
  fallback `claude-fable-5` — resolved from `policies/agents.yaml` by the launchers
  (`scripts/cto-claude.sh`, `scripts/cxo-claude.sh`). ADR 0009 + its 2026-09-23 addendum.
- **Workers** use their role's model from the same file (Sonnet 5 for most roles; Opus 5.5
  for security_engineer and devops_engineer).
- **Codex and Antigravity (agy)** are not a fallback for Claude sessions: they are separate
  runners reached through a brief — `windows/spawn-worker.ps1 -Runner codex|agy`, IRON-RULES
  §53, skill `delegate-external-agent`. **Jules** likewise, through `tools/jules.py`.
- **When Claude quota is out:** wait for the reset or move the work to one of those runners by
  brief. There is no automatic re-routing and no model proxy.
