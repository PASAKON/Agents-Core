# Token saving: auto-compact window (2026-09-25, task-9f6fec26)

## What changed

Every Claude Code session this org launches now auto-compacts at **300,000**
tokens of context instead of the 1M-model default (~967K, per
[code.claude.com/docs/en/model-config](https://code.claude.com/docs/en/model-config)).
Measured 2026-09-25: C-level sessions ran at 850–966k context for 500–1,456
turns, and cache reads (the whole context re-sent every turn) were 63% of the
token bill.

Set in two places:

1. **`claude-home/settings.json`** — top-level key `"autoCompactWindow": 300000`.
   On the Mac this file is symlinked live as `~/.claude/settings.json` (ADR
   0027), so it applies to every Mac session (C-level tabs and workers) as
   soon as the CTO merges this branch to `main`.
2. **Six launchers** — `scripts/spawn-cto.sh`, `scripts/spawn-cxo.sh`,
   `scripts/cto-claude.sh`, `scripts/cxo-claude.sh`, `scripts/spawn-worker.sh`,
   `scripts/spawn-worker-remote.sh` — each now runs
   `: "${CLAUDE_CODE_AUTO_COMPACT_WINDOW:=300000}"; export CLAUDE_CODE_AUTO_COMPACT_WINDOW`
   near their existing exports. This is belt-and-braces for Contabo/winbox,
   where `claude-home/settings.json` is copied (not symlinked) into
   `~/.claude/settings.json` and can go stale between HQ syncs. The env var
   also takes priority over the settings file per the documented priority
   order (env var > CLI flag > `/autocompact` > settings file > model default).

Also added a `## Compact instructions` section to `claude-home/CLAUDE.md`
(global CLAUDE.md, same symlink) telling `/compact` what to keep (session
charter/DoD, task-ids + status + branch, touched file paths, open CEO
questions, last CTO-FEEDBACK, already-measured numbers) and what to drop
(tool output already acted on).

## Verifying inside a session

- `/context` — shows current context usage and the effective auto-compact
  threshold for this session.
- `/usage` — shows token/cost usage for the session.
- Confirm the env var actually landed: `echo "$CLAUDE_CODE_AUTO_COMPACT_WINDOW"`
  should print `300000` inside any C-level or worker shell spawned by the six
  launchers above.

## Weekly check

```bash
python3 tools/token_profile.py --days 7
```

Watch the cache-read share of the token bill and the average context size at
compact time — both should trend down from the 2026-09-25 baseline (63%
cache reads, 850–966k context at compact).

## Rollback

- Remove `"autoCompactWindow": 300000` from `claude-home/settings.json` and
  the six launchers' guarded-export blocks (or just set
  `CLAUDE_CODE_AUTO_COMPACT_WINDOW` to a larger value / unset it before
  launch) to go back to the model's tuned default (~967K for 1M-context
  models).
- `DISABLE_COMPACT=1` (env var) disables all compaction entirely for a
  session — use only for short-lived debugging, never as a standing default,
  since it defeats the whole point of this change.

## Re-deriving claude-home on another box

After pulling this branch to `main`, re-run the installer on each box so
`~/.claude/settings.json` and `~/.claude/CLAUDE.md` pick up the new key/section:

```bash
bash scripts/install-claude-home.sh
```

Use `bash scripts/install-claude-home.sh --check` first on a box you're
unsure about — it reports drift (a real file where a symlink should be, e.g.
a Contabo/winbox copy) without changing anything, exit 1 on drift.
