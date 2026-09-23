# Agents Org Runtime — Environment Context

This file auto-loads into every Claude Code session whose working directory
is this repo — on the Mac (full dev machine) **and** on the Contabo VPS (via
MoonieX Console mobile chat, launched through `scripts/cto-claude.sh`).
Read it to know which machine you're on and which projects you can actually touch.

## Which machine am I on?
- **Mac**: repo lives at `/Users/gob/Projects/Agents`. Every project under
  `/Users/gob/Projects/` is reachable — no restriction.
- **Contabo VPS** (mobile Console sessions): repo lives at
  `/opt/mooniex-agents`. Only repos actually cloned onto this box are
  reachable — everything else needs `git clone` onto the box first.
  Confirm with `hostname` / `pwd` if unsure.

## Project availability on Contabo (mobile Console)

Contabo's work root is `/opt/MoonieXHQ` (same names as the Mac HQ; `/root/MoonieXHQ`
links to it — the real folder sits under `/opt` because `/root` is 0700 and the
secretary/driveup/photoup services must reach Agents/Core). Moved 2026-09-23; every old
path below is a compat link for a week — write the new one.
Plan + record: `docs/ops/contabo-hq-migration-plan-2026-09-23.md`.

| Project | Path on Contabo | Old path (link) |
|---|---|---|
| Agents-Core (this org repo) | `/opt/mooniex-agents` — moves to `Agents/Core` last | — |
| MoonieX-Console | `/opt/MoonieXHQ/Projects/MoonieX/Console` | `/opt/mooniex-console` |
| MoonieX-ClaudeFlow | `/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow` | `/root/projects/mooniex-claudeflow` |
| MoonieX-Option | `/opt/MoonieXHQ/Projects/MoonieX/Option` | `/root/projects/mooniex-option` |
| MoonieX-AlphaTrader | `/opt/MoonieXHQ/Projects/MoonieX/AlphaTrader` | `/root/projects/mooniex-alphatrader` |
| MoonieX-LineAutomation | `/opt/MoonieXHQ/Projects/MoonieX/LineAutomation` | `/root/projects/mooniex-line-automation` |
| LinePoster (no repo) | `/opt/MoonieXHQ/Projects/MoonieX/LinePoster` | `/root/projects/mooniex-line-poster` |
| LungNote-MCP | `/opt/MoonieXHQ/Projects/LungNote/Mcp` | `/opt/lungnote-mcp` |
| claude-usage-monitor (tool, stays outside) | `/opt/claude-usage-monitor` | — |

Compose projects keep their old names (`COMPOSE_PROJECT_NAME` pinned in each `.env`), so
`docker compose` run from the new folder manages the same containers.

**NOT on Contabo yet** — a mobile/Console session cannot edit these until someone
clones them onto the box: `mooniex-webapp`,
`mooniex-remotion`, `mooniex-wa-system`, `mooniex-company`, `mooniex-nohuman`,
`mooniex-website-templete`, `mooniex-hyperframes`, `mooniex-claudesign`,
`mooniex-controller-system`, `mooniex-scriptable` (the iOS-side source).

**PARKED 2026-08-03** — pushed to GitHub and archived (read-only); the local
folders carry a `PARKED-` prefix. Do not start work in these without CEO
sign-off: `PARKED-mooniex-video-engine`, `PARKED-mooniex-moonx`. Retired the
same day: `mooniex-genui` (GitHub repo renamed `DELETE-MoonieX-Website`,
superseded by `MoonieX-Design`).

If a task needs one of the "NOT on Contabo" repos from a mobile session, say so
explicitly and tell the CEO it needs cloning onto Contabo first — don't silently
attempt it or assume GitHub presence is enough.

## Wiki access

Wiki tools (`wiki_read`/`wiki_write`/etc.) are multi-root and namespaced. Roots
are declared in `config/wikis.yaml` (ADR 0013): **`org:`** = `Agents-Wikis`, the
org runtime rules that bind every agent on every project; **`mooniex:`** =
`MoonieX-Wikis`, MoonieX product facts, and the default namespace when a path
carries no prefix.

| | Mac | Contabo |
|---|---|---|
| `org:` | ✅ `/Users/gob/MoonieXHQ/Agents/Rules` | ✅ `/opt/MoonieXHQ/Agents/Rules` |
| `mooniex:` | ✅ `/Users/gob/MoonieXHQ/Agents/Wikis` | ✅ `/opt/MoonieXHQ/Agents/Wikis` (CEO 2026-08-09) |

**Both namespaces resolve on Contabo.** `org:` landed 2026-08-03 with the
ADR-0013 split; `mooniex:` followed on 2026-08-09, which also fixed every
UNPREFIXED path on that box — those had been failing because `mooniex` is the
default namespace, so `wiki_read('INDEX.md')` resolved to a root that was not
there. Prefixing with `org:` is no longer required.

`config/wikis.yaml` carries Mac absolute paths; `cto-claude.sh` /
`cxo-claude.sh` export `WIKI_ROOT_ORG=/opt/MoonieXHQ/Agents/Rules` and
`WIKI_ROOT_MOONIEX=/opt/MoonieXHQ/Agents/Wikis` (old `/opt/*-wikis` as fallback) when those directories exist, which is
how Contabo resolves them. Any namespace can be repointed the same way with
`WIKI_ROOT_<NS>`.

⚠️ **Contabo's copies are rsync snapshots, not git checkouts** — neither has a
`.git`, so there is nothing to pull and nothing to push. They go stale as soon
as the Mac's wiki changes, and a `wiki_write` on that box edits a copy the next
sync silently overwrites. Treat Contabo wikis as **read-only** and refresh after
any significant wiki change (run from the Mac):

```bash
rsync -aH --delete --exclude '.git/' /Users/gob/MoonieXHQ/Agents/Wikis/         mooniex-vps:/opt/MoonieXHQ/Agents/Wikis/
rsync -aH --delete --exclude '.git/' /Users/gob/MoonieXHQ/Agents/Rules/ mooniex-vps:/opt/MoonieXHQ/Agents/Rules/
```

## Maintenance

Whenever a repo is cloned onto (or removed from) the Contabo box, update BOTH:
1. The table above.
2. Wiki `projects/mooniex-console.md` §"Project availability" (Mac session only).
