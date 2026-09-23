# Note for the Contabo HQ move — Cookie Run teacher loop (cto-6ebacd0e, 2026-09-23)

Per `contabo-hq-migration-plan-2026-09-23.md` ("leave a file in the repo"): one
thing of mine hard-codes the current Agents/Core path.

- **root crontab**, added 2026-09-23 (CEO go):
  `30 22 * * * cd /opt/mooniex-agents && ... python3 tools/cookierun_teachers.py daily >> state/cookierun_teachers/daily.log 2>&1`
  When Agents/Core moves to `/opt/MoonieXHQ/Agents/Core`, change the `cd` path.
  The compat symlink keeps it working for the week it exists.
- State it writes: `state/cookierun_teachers/` (watermark, ledgers, daily reports) — moves with the repo.
- Data it reads: `/opt/MoonieXHQ/Assets/MoonieX/CookierunBot/cookierun-gold` (already the new path).
