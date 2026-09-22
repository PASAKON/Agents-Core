# claude-home/ — the org's half of `~/.claude`, tracked (ADR 0027)

`~/.claude` is Claude Code's own state dir. Everything in it that the MoonieX
org *depends on* lives here and is **linked** into place by
`scripts/install-claude-home.sh`. Delete `~/.claude`, reinstall Claude Code,
`claude login`, run the script — the org is back.

| here | linked at | what |
|---|---|---|
| `CLAUDE.md` | `~/.claude/CLAUDE.md` | global instructions (every session, every project) |
| `settings.json` | `~/.claude/settings.json` | hooks (GateGuard, tab_guard, skill-log, caveman, allowlist, cost-guardian), statusline, plugins, permissions, model |
| `settings.local.json.example` | copied once to `~/.claude/settings.local.json` | local permissions — never linked, never overwritten |
| `hooks/` | `~/.claude/hooks` | caveman ×4, allowlist ×2, office ×4 (+ package.json) |
| `commands/` | `~/.claude/commands` | `/spawn-cto` `/spawn-cfo` `/spawn-cgo` `/spawn-cmo` |
| `mcp/mooniex-coord/` | `~/.claude/mcp/mooniex-coord` | coord-bus MCP server |
| `tools/` | `~/.claude/tools` | `prune_transcripts.py` (launchd), `wt_steps.py`, 2 drafts |
| `launchd/*.plist` | `~/Library/LaunchAgents/` | `com.gob.claude-prune-transcripts` |
| `assets/hyperframes-media/` | `~/.claude/skills/hyperframes-media` | assets, not a skill |
| `skills.txt` | `~/.claude/skills/<name>` → target | **the map**: 46 rows; a real dir with no row is drift |
| `plugins.txt` | plugin registry | 5 marketplaces, 4 plugins, reinstalled by the script |

Org **skills** are not here — they live in `.claude/skills/` (the repo's project
skills, under skill-lint); `skills.txt` links the user-level ones.

## One-time migration (CEO runs it — the auto-mode classifier refuses to move private config into a pushed repo by itself)
```bash
python3 scripts/claude_home_migrate.py        # moves the files listed above out of ~/.claude, leaves symlinks, writes a rollback manifest
bash scripts/install-claude-home.sh --check   # must say clean
git add claude-home .claude/skills && git commit
```
Rollback: `python3 scripts/claude_home_migrate.py --rollback state/claude-home-migration-<ts>.json`.

## Verbs (every day after)
```bash
bash scripts/install-claude-home.sh          # link, seed, plugins, launchd, reel-editor-th venv — idempotent
bash scripts/install-claude-home.sh --check  # doctor; exit 1 on DRIFT / MISSING / UNMAPPED; changes nothing
```
A live edit to `settings.json` goes through the symlink into this repo — commit it.
If Claude Code ever replaces the symlink with a real file, `--check` says DRIFT
and the next install CAPTURES the live copy into the repo before relinking.

## Deliberately not tracked (still in `~/.claude`)
- `projects/` — session transcripts, 9.5 GB. Read by `/session-list`, session search, statusline. History, not config; pruned by the launchd job.
- `plugins/`, `cache/`, `file-history/`, `shell-snapshots/`, `telemetry/`, `logs/` — reinstallable / ephemeral.
- `daemon/` — Claude Code's own cc-daemon state. `daemons/inbox-listener.mjs` — dead ClaudeFlow mesh listener (2026-05-18, not in launchd).
- `skills/synced`, `skills/learned` — Claude's own.
- `.claude/skills/reel-editor-th/{.venv,assets}` — venv rebuilt from `requirements.txt`; the 210 MB b-roll is media → Assets/ + Drive.
- Credentials — macOS Keychain (`Claude Code-credentials`), survive a delete.
