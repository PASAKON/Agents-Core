# `.agents/` — externally installed, not org-authored

This directory is a third-party skill pack (currently `.agents/skills/`, ~91
wealth-management skills: account-maintenance, anti-money-laundering,
know-your-customer, etc.) installed via `npx skills add`. It is **not**
written or maintained by this org, is not referenced by anything under
`.claude/skills/`, and is intentionally excluded from git (see `.gitignore`).

If you're looking for this content and it's missing after a fresh clone:
that's expected, not a bug. Re-run the installer that pulled it in, or ask
whoever set it up which package/source to re-fetch from.
