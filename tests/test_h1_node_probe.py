"""PLAN-auto-dispatch row H1 (task-25c272ce): the node probe measures cpus,
load per core and installed runners, and writes them to the `hosts` table.

Covers: the three new `hosts` columns and `upsert_host`, the migration of an
old ledger that lacks them, `tools.node_dispatch.verb_probe` with the OS calls
replaced, the Windows and error paths (None, never a crash), and the timer
files (launchd plist, systemd service and timer) that run the probe every 60 s.

SQLite only, same convention as tests/test_node_dispatch.py -- point lib.db at
a tmp_path ledger via monkeypatch, never the real state/tasks.db (ADR 0021).

Run:  .venv/bin/python -m pytest tests/test_h1_node_probe.py
"""
from __future__ import annotations

import json
import plistlib
import re
from pathlib import Path

import pytest

from lib import config as config_mod
from lib import db as db_mod
from lib import db_pg
from tools import node_dispatch as nd

ROOT = Path(nd.ROOT)
PLIST = ROOT / "scripts" / "com.mooniex.node-probe.plist"
SERVICE = ROOT / "deploy" / "systemd" / "node-probe.service"
TIMER = ROOT / "deploy" / "systemd" / "node-probe.timer"
NEW_COLUMNS = ("cpus", "load_per_core", "runners")


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE",
                "SSH_ORIGINAL_COMMAND", "SSH_CLIENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(config_mod, "self_host", lambda: "mac")
    # Not under test, and the real ones shell out to vm_stat and git.
    monkeypatch.setattr(nd, "_ram_free_gb", lambda: 8.0)
    monkeypatch.setattr(nd, "_git_version", lambda: "abc1234")


def _which_only(*present: str):
    return lambda name, *a, **kw: f"/fake/bin/{name}" if name in present else None


def _hosts_columns() -> set[str]:
    with db_mod.get_conn() as conn:
        return {r["name"] for r in conn.execute("PRAGMA table_info(hosts)").fetchall()}


def _stub_machine(monkeypatch, *, cpus=4, load=2.0, runners=("claude", "agy")):
    monkeypatch.setattr(nd, "_is_windows", lambda: False)
    monkeypatch.setattr(nd.os, "cpu_count", lambda: cpus)
    monkeypatch.setattr(nd.os, "getloadavg", lambda: (load, 0.0, 0.0))
    monkeypatch.setattr(nd.shutil, "which", _which_only(*runners))


# ---------------------------------------------------------------------------
# verb_probe writes the new columns
# ---------------------------------------------------------------------------

def test_probe_writes_cpus_load_per_core_and_runners(monkeypatch):
    _stub_machine(monkeypatch, cpus=4, load=2.0, runners=("claude", "agy"))

    out = nd.dispatch("probe", [])

    assert out["ok"] is True, out
    r = out["result"]
    assert (r["cpus"], r["load_per_core"], r["runners"]) == (4, 0.5, ["agy", "claude"])
    h = db_mod.get_host("mac")
    assert h["cpus"] == 4
    assert h["load_per_core"] == 0.5
    assert json.loads(h["runners"]) == ["agy", "claude"]


def test_probe_keeps_todays_fields_and_join_state(monkeypatch):
    _stub_machine(monkeypatch)
    db_mod.upsert_host("mac", os="darwin", agents_root="/x", status="online",
                       max_workers=4)

    r = nd.dispatch("probe", [])["result"]

    for key in ("host", "os", "agents_root", "free_gb", "ram_free_gb", "running",
                "version"):
        assert key in r, key
    assert (r["host"], r["version"], r["ram_free_gb"]) == ("mac", "abc1234", 8.0)
    h = db_mod.get_host("mac")
    assert (h["os"], h["agents_root"], h["status"], h["max_workers"]) == (
        "darwin", "/x", "online", 4)
    assert h["probed_at"] and h["version"] == "abc1234"


def test_runners_are_sorted_whatever_order_which_answers(monkeypatch):
    _stub_machine(monkeypatch, runners=("codex", "agy", "claude"))
    assert nd._installed_runners() == ["agy", "claude", "codex"]


def test_runners_ignore_clis_outside_the_three(monkeypatch):
    _stub_machine(monkeypatch, runners=("codex", "gemini", "aider"))
    assert nd._installed_runners() == ["codex"]


@pytest.mark.parametrize("load, cpus, want", [
    (1.23456, 3, 0.41),
    (0.0, 8, 0.0),
    (16.0, 8, 2.0),   # overloaded: above 1.0 per core is a real answer, not clamped
])
def test_load_per_core_rounds_to_two_places(monkeypatch, load, cpus, want):
    _stub_machine(monkeypatch, cpus=cpus, load=load)
    assert nd._cpu_facts() == (cpus, want)


# ---------------------------------------------------------------------------
# Windows and error paths: None, never a crash
# ---------------------------------------------------------------------------

def test_windows_has_no_load_but_the_probe_still_lands(monkeypatch):
    _stub_machine(monkeypatch, cpus=8, runners=("claude",))
    monkeypatch.setattr(nd, "_is_windows", lambda: True)
    monkeypatch.delattr(nd.os, "getloadavg", raising=False)  # absent on Windows

    out = nd.dispatch("probe", [])

    assert out["ok"] is True, out
    assert (out["result"]["cpus"], out["result"]["load_per_core"]) == (8, None)
    h = db_mod.get_host("mac")
    assert h["cpus"] == 8 and h["load_per_core"] is None
    assert json.loads(h["runners"]) == ["claude"]


def test_getloadavg_error_gives_none_not_a_crash(monkeypatch):
    _stub_machine(monkeypatch)

    def boom():
        raise OSError("getloadavg failed")

    monkeypatch.setattr(nd.os, "getloadavg", boom)

    assert nd._cpu_facts() == (4, None)
    out = nd.dispatch("probe", [])
    assert out["ok"] is True, out
    assert db_mod.get_host("mac")["load_per_core"] is None


def test_unknown_cpu_count_gives_none_for_both(monkeypatch):
    _stub_machine(monkeypatch)
    monkeypatch.setattr(nd.os, "cpu_count", lambda: None)  # os.cpu_count() may say so

    assert nd._cpu_facts() == (None, None)  # no ZeroDivisionError, no TypeError
    assert nd.dispatch("probe", [])["ok"] is True
    h = db_mod.get_host("mac")
    assert h["cpus"] is None and h["load_per_core"] is None


def test_cpu_count_that_raises_gives_none_for_both(monkeypatch):
    _stub_machine(monkeypatch)

    def boom():
        raise NotImplementedError

    monkeypatch.setattr(nd.os, "cpu_count", boom)
    assert nd._cpu_facts() == (None, None)


def test_no_runner_installed_is_an_empty_list_not_null(monkeypatch):
    _stub_machine(monkeypatch, runners=())

    assert nd.dispatch("probe", [])["ok"] is True

    # "[]" = probed, none found. NULL would mean never probed with this field.
    assert db_mod.get_host("mac")["runners"] == "[]"


# ---------------------------------------------------------------------------
# upsert_host and the `hosts` schema
# ---------------------------------------------------------------------------

def test_new_columns_exist_on_a_fresh_ledger():
    assert set(NEW_COLUMNS) <= _hosts_columns()


def test_upsert_host_stores_and_encodes_runners():
    db_mod.upsert_host("contabo", cpus=6, load_per_core=0.12,
                       runners=["claude", "codex", "agy"])

    h = db_mod.get_host("contabo")
    assert (h["cpus"], h["load_per_core"]) == (6, 0.12)
    assert h["runners"] == '["claude", "codex", "agy"]'


def test_upsert_host_leaves_untouched_columns_alone():
    db_mod.upsert_host("mac", os="darwin", agents_root="/x", provides=["chrome"],
                       max_workers=4, status="online", free_gb=10.0,
                       cpus=8, load_per_core=0.3, runners=["claude"])

    db_mod.upsert_host("mac", running=2)  # one column, nothing else

    h = db_mod.get_host("mac")
    assert h["running"] == 2
    assert (h["os"], h["agents_root"], h["max_workers"], h["status"], h["free_gb"]) == (
        "darwin", "/x", 4, "online", 10.0)
    assert h["provides"] == '["chrome"]'
    assert (h["cpus"], h["load_per_core"], h["runners"]) == (8, 0.3, '["claude"]')


def test_upsert_host_with_only_new_columns_leaves_the_rest_alone():
    db_mod.upsert_host("mac", os="darwin", status="online", running=3, free_gb=9.5)

    db_mod.upsert_host("mac", cpus=8, load_per_core=0.4, runners=["agy"])

    h = db_mod.get_host("mac")
    assert (h["os"], h["status"], h["running"], h["free_gb"]) == (
        "darwin", "online", 3, 9.5)


def test_upsert_host_none_is_a_write_that_clears_only_that_column():
    db_mod.upsert_host("mac", cpus=8, load_per_core=0.4, runners=["agy"])

    db_mod.upsert_host("mac", load_per_core=None)  # a reading that failed

    h = db_mod.get_host("mac")
    assert h["load_per_core"] is None
    assert (h["cpus"], h["runners"]) == (8, '["agy"]')


def test_reseed_from_config_keeps_the_new_columns(monkeypatch):
    monkeypatch.setattr(config_mod, "hosts", lambda: {
        "mac": {"os": "darwin", "agents_root": "/x", "provides": ["chrome"],
                "max_workers": 4},
    })
    db_mod.seed_hosts_from_config()
    db_mod.upsert_host("mac", cpus=8, load_per_core=0.3, runners=["claude"])

    db_mod.seed_hosts_from_config()

    h = db_mod.get_host("mac")
    assert (h["cpus"], h["load_per_core"], h["runners"]) == (8, 0.3, '["claude"]')


def test_upsert_host_still_rejects_an_unknown_column():
    with pytest.raises(ValueError, match="unknown host column"):
        db_mod.upsert_host("mac", cpu_count=4)


# ---------------------------------------------------------------------------
# an old ledger migrates
# ---------------------------------------------------------------------------

_OLD_HOSTS = """
DROP TABLE hosts;
CREATE TABLE hosts (
    host         TEXT PRIMARY KEY,
    os           TEXT,
    hq_root      TEXT,
    agents_root  TEXT,
    provides     TEXT,
    max_workers  INTEGER,
    status       TEXT,
    probed_at    TEXT,
    free_gb      REAL,
    ram_free_gb  REAL,
    running      INTEGER,
    version      TEXT,
    updated_at   TEXT
);
"""


def _downgrade_hosts_table() -> None:
    with db_mod.get_conn() as conn:
        conn.executescript(_OLD_HOSTS)
        conn.execute(
            "INSERT INTO hosts (host, os, status, running, free_gb) "
            "VALUES ('winbox', 'windows', 'online', 1, 50.0)")


def test_old_ledger_without_the_columns_migrates_and_keeps_its_rows():
    _downgrade_hosts_table()
    assert not set(NEW_COLUMNS) & _hosts_columns()

    db_mod.init()

    assert set(NEW_COLUMNS) <= _hosts_columns()
    h = db_mod.get_host("winbox")
    assert (h["os"], h["status"], h["running"], h["free_gb"]) == (
        "windows", "online", 1, 50.0)
    assert (h["cpus"], h["load_per_core"], h["runners"]) == (None, None, None)


def test_migration_is_idempotent_and_a_probe_works_after_it(monkeypatch):
    _downgrade_hosts_table()
    db_mod.init()
    db_mod.init()  # a second ADD COLUMN would raise "duplicate column name"
    _stub_machine(monkeypatch, cpus=2, load=1.0, runners=("claude",))

    assert nd.dispatch("probe", [])["ok"] is True

    h = db_mod.get_host("mac")
    assert (h["cpus"], h["load_per_core"], json.loads(h["runners"])) == (
        2, 0.5, ["claude"])


def test_hosts_migration_list_names_exactly_the_new_columns():
    assert [c for c, _ in db_mod._HOSTS_MIGRATION] == list(NEW_COLUMNS)
    assert set(NEW_COLUMNS) <= db_mod._HOST_COLUMNS


def test_postgres_side_uses_the_same_migration_loop():
    """No PG_SCHEMA change: init_schema() runs the ADD COLUMN loop on top of it
    for both backends, and reads the existing columns through PRAGMA
    table_info(hosts), which db_pg translates. The ALTER needs no translation."""
    sql = db_pg._translate("PRAGMA table_info(hosts)")
    assert sql and "information_schema.columns" in sql and "'hosts'" in sql
    for col, coltype in db_mod._HOSTS_MIGRATION:
        ddl = f"ALTER TABLE hosts ADD COLUMN {col} {coltype}"
        assert db_pg._translate(ddl) == ddl


# ---------------------------------------------------------------------------
# timer files
# ---------------------------------------------------------------------------

def _unit(path: Path) -> dict[str, list[tuple[str, str]]]:
    """A systemd unit as {section: [(key, value), ...]}. Repeated keys
    (two Environment= lines) are kept, comments and blanks dropped."""
    out: dict[str, list[tuple[str, str]]] = {}
    section = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            out[section] = []
        else:
            key, _, value = line.partition("=")
            out[section].append((key, value))
    return out


def _values(unit: dict, section: str, key: str) -> list[str]:
    return [v for k, v in unit[section] if k == key]


def test_plist_runs_the_probe_every_60_seconds():
    plist = plistlib.loads(PLIST.read_bytes())

    assert plist["Label"] == "com.mooniex.node-probe"
    assert plist["StartInterval"] == 60
    # through the hub env wrapper: launchd has no ORG_DB_URL, and since G1
    # state/tasks.db is a tombstone (docs/ops/node-dispatch.md)
    assert plist["ProgramArguments"] == [
        "/bin/bash",
        "/Users/gob/MoonieXHQ/Agents/Core/scripts/hub/with-org-db-env.sh",
        "/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python",
        "-m", "tools.node_dispatch", "probe",
    ]
    assert plist["WorkingDirectory"] == "/Users/gob/MoonieXHQ/Agents/Core"
    log = "/Users/gob/MoonieXHQ/Agents/Core/state/logs/node-probe.log"
    assert plist["StandardOutPath"] == log
    assert plist["StandardErrorPath"] == log


def test_plist_path_reaches_the_dir_where_claude_and_agy_live():
    """launchd's own PATH is short. Without ~/.local/bin the probe reports
    runners as ["codex"] only, and H2 would never route to claude or agy."""
    path = plistlib.loads(PLIST.read_bytes())["EnvironmentVariables"]["PATH"]
    assert "/Users/gob/.local/bin" in path.split(":")


def test_the_command_the_timers_run_is_a_real_cli_entry():
    assert "probe" in nd.HANDLERS
    assert nd._ARGSPEC["probe"] == ()  # the timers pass no argument


def test_service_is_a_oneshot_that_runs_the_probe_on_contabo():
    unit = _unit(SERVICE)

    assert _values(unit, "Service", "Type") == ["oneshot"]
    assert _values(unit, "Service", "ExecStart") == [
        "/bin/bash /opt/MoonieXHQ/Agents/Core/scripts/hub/with-org-db-env.sh "
        "/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m tools.node_dispatch probe"]
    assert _values(unit, "Service", "WorkingDirectory") == ["/opt/MoonieXHQ/Agents/Core"]
    env = _values(unit, "Service", "Environment")
    assert "ORG_HOST=contabo" in env
    (path,) = [e for e in env if e.startswith("PATH=")]
    assert "/root/.local/bin" in path[len("PATH="):].split(":")


def test_timer_fires_at_boot_plus_60s_then_every_60s_after_the_last_run():
    unit = _unit(TIMER)

    assert _values(unit, "Timer", "OnBootSec") == ["60"]
    assert _values(unit, "Timer", "OnUnitActiveSec") == ["60"]
    assert _values(unit, "Install", "WantedBy") == ["timers.target"]
    # a timer triggers the service of the same name; no Unit= override needed
    assert SERVICE.name == TIMER.name.replace(".timer", ".service")
    assert not _values(unit, "Timer", "Unit")


@pytest.mark.parametrize("path", [PLIST, SERVICE, TIMER], ids=lambda p: p.name)
def test_timer_files_say_which_ledger_and_when_it_helps(path):
    text = path.read_text()
    assert "lib.db resolves" in text
    assert "G1" in text and "with-org-db-env.sh" in text  # the hub, never the tombstone


@pytest.mark.parametrize("path", [PLIST, SERVICE, TIMER], ids=lambda p: p.name)
def test_timer_files_carry_no_secret(path):
    text = path.read_text()
    assert not re.search(r"(?i)(token|secret|password|api[_-]?key)\s*[=:<]", text)
    assert not re.search(r"(?i)postgres(ql)?://", text)
