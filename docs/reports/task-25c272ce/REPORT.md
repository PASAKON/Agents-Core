# task-25c272ce — H1: probe measures CPU per core + installed runners

PLAN-auto-dispatch §4, row H1. Branch `agent/developer-task-25c272ce`. Nothing installed, no ssh.

## Files changed

- `lib/db.py` — new `_HOSTS_MIGRATION` (`cpus INTEGER`, `load_per_core REAL`, `runners TEXT`), applied in `init_schema()` through the same existence-checked `ALTER TABLE ADD COLUMN` loop the file uses for `tasks` and `c_level_sessions`. `_HOST_COLUMNS` gains the three names. `upsert_host` JSON-encodes `runners` the way it already did `provides`. `tasks` untouched.
- `lib/db_pg.py` — comment only. `hosts` is created in `PG_SCHEMA`, and the same `init_schema()` loop adds the columns on Postgres (`PRAGMA table_info(hosts)` is already translated), so no DDL change was needed.
- `tools/node_dispatch.py` — `verb_probe` also measures and writes `cpus`, `load_per_core`, `runners` and returns them. New helpers `_cpu_facts()` and `_installed_runners()`. Today's fields and behaviour unchanged.
- `scripts/com.mooniex.node-probe.plist` — new, `StartInterval` 60, `RunAtLoad`, runs `<venv python> -m tools.node_dispatch probe`, `WorkingDirectory` `/Users/gob/MoonieXHQ/Agents/Core`, log `state/logs/node-probe.log`.
- `deploy/systemd/node-probe.service` — new, oneshot, `Environment=ORG_HOST=contabo`.
- `deploy/systemd/node-probe.timer` — new, `OnBootSec=60`, `OnUnitActiveSec=60`.
- `tests/test_h1_node_probe.py` — new, 34 tests.
- `docs/reports/task-25c272ce/REPORT.md` — this file.

## What was done

- **Migration path.** The brief named `_MIGRATION_COLUMNS` / the VALID set. Both are `tasks`-only, and `scripts/test_db_delegate_log.py:47` and `scripts/test_depends_on_enforcement.py:338` iterate `_MIGRATION_COLUMNS` and ALTER `tasks`, so a hosts column there would have broken them. `hosts` had no ALTER path at all (`CREATE TABLE IF NOT EXISTS` does not upgrade an old table). `_HOSTS_MIGRATION` is the parallel list, same shape as `_C_LEVEL_SESSION_MIGRATION`.
- **Probe values.** `cpus = os.cpu_count()`. `load_per_core = round(os.getloadavg()[0] / cpus, 2)`, `None` on Windows, on any error, or when the CPU count is unknown. `runners` = sorted of claude/codex/agy that `shutil.which` finds; none found writes `"[]"`, not NULL, so "probed, none" and "never probed" differ.
- **PATH in the timer files (not in the brief).** The model file `com.mooniex.quota-snapshot.plist` sets `PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`. On this Mac `claude` and `agy` live in `/Users/gob/.local/bin`. Measured under `env -i`: that PATH gives `['codex']`; with `~/.local/bin` first it gives `['agy','claude','codex']`. The plist adds it. The systemd unit sets `PATH` with `/root/.local/bin` and `/root/.npm-global/bin` (where `spawn-worker-remote.sh` looks for the CLIs); systemd's default PATH has neither. Tests pin both.
- **Comment in all three files:** the probe writes to whichever ledger `lib.db` resolves, and is only useful to other hosts after the shared ledger (W1.10).
- Real probe on this Mac against a scratch ledger: `cpus 8, load_per_core 1.36, runners ["agy","claude","codex"]`.

## Tests

Quoted from the runs (worktree, `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python`):

- `python -m pytest -p no:warnings` (default host): `3576 passed, 27 skipped in 316.71s (0:05:16)`, exit 0.
- `ORG_HOST=contabo python -m pytest -p no:warnings`: `3576 passed, 27 skipped in 288.69s (0:04:48)`, exit 0.
- `python scripts/test_org_tools_registry.py`: 29 `[PASS]`, 0 `[FAIL]`, `ALL PASS`, exit 0.
- `python scripts/test_mcp_role_config.py`: 57 `[PASS]`, 0 `[FAIL]`, `OK — 0 failure(s)`, exit 0.
- New file alone, with the neighbours (`test_node_dispatch`, `test_db_hosts_letters`, `test_db_pg_translate`): `192 passed`.
- No test outside the touch list pinned old behaviour. `pytest.ini` carries `addopts = -q`; I passed no `-q` of my own.
- Not run: the Postgres round-trip in `tests/test_db_backend_pg.py` (gated on `ORG_TEST_DB_URL`, skipped). Only the PG translation of the PRAGMA and ALTER statements is covered.
- `plutil -lint` on the plist: OK.

## Blockers

None. Two things the CTO should decide or know before the timers are installed:

1. **Order matters.** Probing a ledger that has not run the new `db.init()` fails: measured `OperationalError: table hosts has no column named cpus`, and it succeeds after one `db.init()`. Any daemon start does the init (the watchdog does it at boot), and the plist and unit comments say to init once before enabling. If you would rather the probe self-heal, it is one line in `verb_probe`, but that changes "keep today's behaviour", so I left it out.
2. **The same short-PATH trap is likely on the ssh path.** H2 will probably call `probe` over the `org_dispatch` ssh key, and sshd gives a non-interactive command a minimal PATH. I did not test this (no ssh allowed), so treat it as unverified. If it holds, `runners` would be wrong for every remote read.

## Skill learning

- MISSING [no owner] : a launchd/systemd timer that calls `shutil.which` for `claude`/`codex`/`agy` needs `~/.local/bin` (Mac) or `/root/.local/bin` (Contabo) in its PATH; the repo's own model plist, `scripts/com.mooniex.quota-snapshot.plist`, does not have it and would have reported `['codex']` only · evidence: `env -i PATH=…` run above, task-25c272ce · to memory as a reference note, or a line in whoever owns the timer templates.
- MISSING [CXO_Protocol_DevSpawn §brief] : "same migration path as tasks.runner_model" is ambiguous. `_MIGRATION_COLUMNS`/`VALID_COLUMNS` are tasks-only and two scripts iterate them, so `hosts` needs its own list; the brief should name the list or the table · evidence: `lib/db.py:205`, `scripts/test_db_delegate_log.py:47`, commit b0211875.
- COSTLY [no owner] : GateGuard fires once per new file even for several new files written in one message (two of three parallel Writes were refused), and again on Edit per file; 10 refused calls in this task · prevented by: already written down in `~/.claude/CLAUDE.md` "GateGuard fact protocol"; batching new files in one message does not help, so write them one at a time.
