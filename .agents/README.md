# `.agents/` — externally installed, not org-authored

This directory is a third-party skill pack (currently `.agents/skills/`, ~91
wealth-management skills: account-maintenance, anti-money-laundering,
know-your-customer, etc.) installed via `npx skills add`. It is **not**
written or maintained by this org, is not referenced by anything under
`.claude/skills/`, and is intentionally excluded from git (see `.gitignore`).

If you're looking for this content and it's missing after a fresh clone:
that's expected, not a bug. Re-run the installer that pulled it in, or ask
whoever set it up which package/source to re-fetch from.

## Parked since 2026-11-19 (Claude CTO + AGY CTO, docs/design/cto-pair.md)

AGY loads `.agents/skills/` before `.claude/skills/` under a context budget; the ~91 finance skills pushed
41 org skills out of it. They now sit in `.agents/parked-finance-skills/` (still ignored by git, nothing
deleted), and `.agents/skills/` holds only tracked org skills (`takeover`). New org skills go in
`.claude/skills/`. Check a host with `python tools/agy_kit_check.py` (exit 1 on drift).
