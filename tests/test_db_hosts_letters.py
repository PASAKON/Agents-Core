"""Org Mesh W2.1 (docs/design/org-mesh.md C2/C3/C4): the `hosts` and
`letters` tables lib.db.init_schema() creates, plus the read/write helpers
around them.

SQLite only, same convention as tests/test_session_charter.py -- point
lib.db at a tmp_path ledger via monkeypatch, never the real state/tasks.db
(ADR 0021). The Postgres-side SQL is covered separately: pure translation
sanity in tests/test_db_pg_translate.py, and a gated round-trip in
tests/test_db_backend_pg.py (ORG_TEST_DB_URL).

Run:  .venv/bin/python -m pytest tests/test_db_hosts_letters.py
"""
from __future__ import annotations

import pytest

from lib import config as config_mod
from lib import db as db_mod


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    monkeypatch.delenv("CTO_SESSION_ID", raising=False)
    monkeypatch.delenv("CXO_SESSION_ID", raising=False)
    monkeypatch.delenv("CXO_ROLE", raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")


# ---------------------------------------------------------------------------
# schema / init
# ---------------------------------------------------------------------------

def test_init_on_existing_ledger_adds_both_tables_and_keeps_tasks():
    """init() re-run against a ledger that already has task rows (from
    before hosts/letters existed) must add the two new tables without
    touching what's already there."""
    tid = db_mod.create_task("projA", "developer", "t1", "d1")

    db_mod.init()  # second run -- CREATE TABLE IF NOT EXISTS must no-op cleanly

    with db_mod.get_conn() as conn:
        tables = {
            r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "hosts" in tables
    assert "letters" in tables
    assert db_mod.get_task(tid)["id"] == tid  # untouched


def test_init_is_idempotent_for_new_tables():
    db_mod.init()
    db_mod.init()
    with db_mod.get_conn() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(hosts)").fetchall()}
    for expected in ("host", "os", "hq_root", "agents_root", "provides",
                      "max_workers", "status", "probed_at", "free_gb",
                      "ram_free_gb", "running", "version", "updated_at"):
        assert expected in cols, f"missing hosts column {expected!r}: {cols}"
    with db_mod.get_conn() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(letters)").fetchall()}
    for expected in ("id", "to_host", "to_role", "to_session", "from_role",
                      "from_session", "body", "status", "created_at",
                      "delivered_at", "attempts", "last_error"):
        assert expected in cols, f"missing letters column {expected!r}: {cols}"


# ---------------------------------------------------------------------------
# hosts
# ---------------------------------------------------------------------------

def test_upsert_and_get_host_roundtrip():
    db_mod.upsert_host("mac", os="darwin", agents_root="/x", provides=["chrome"],
                        max_workers=4)
    h = db_mod.get_host("mac")
    assert h["host"] == "mac"
    assert h["os"] == "darwin"
    assert h["max_workers"] == 4
    assert h["provides"] == '["chrome"]'
    assert h["updated_at"]


def test_get_host_missing_returns_none():
    assert db_mod.get_host("nope") is None


def test_upsert_host_only_touches_passed_columns():
    db_mod.upsert_host("mac", os="darwin", agents_root="/x")
    db_mod.upsert_host("mac", status="online", probed_at="2026-09-29T00:00:00+00:00",
                        free_gb=12.5, ram_free_gb=4.0, running=2, version="1.2.3")
    h = db_mod.get_host("mac")
    # identity fields from the first call survive the second, probe-only call
    assert h["os"] == "darwin"
    assert h["agents_root"] == "/x"
    # probe fields from the second call all landed
    assert h["status"] == "online"
    assert h["free_gb"] == 12.5
    assert h["running"] == 2
    assert h["version"] == "1.2.3"


def test_upsert_host_rejects_unknown_column():
    with pytest.raises(ValueError, match="unknown host column"):
        db_mod.upsert_host("mac", bogus="x")


def test_list_hosts_sorted_by_host():
    db_mod.upsert_host("winbox", os="windows")
    db_mod.upsert_host("contabo", os="linux")
    db_mod.upsert_host("mac", os="darwin")
    names = [h["host"] for h in db_mod.list_hosts()]
    assert names == ["contabo", "mac", "winbox"]


def test_seed_hosts_from_config_creates_one_row_per_host(monkeypatch):
    monkeypatch.setattr(config_mod, "hosts", lambda: {
        "mac": {"os": "darwin", "agents_root": "/Users/gob/x",
                "provides": ["chrome", "gpu"], "max_workers": 4},
        "contabo": {"os": "linux", "agents_root": "/opt/x",
                    "provides": ["always_on"], "max_workers": 3},
    })

    db_mod.seed_hosts_from_config()

    rows = {h["host"]: h for h in db_mod.list_hosts()}
    assert set(rows) == {"mac", "contabo"}
    assert rows["mac"]["os"] == "darwin"
    assert rows["mac"]["max_workers"] == 4
    assert rows["contabo"]["agents_root"] == "/opt/x"


def test_seed_hosts_from_config_is_idempotent_and_keeps_probe_fields(monkeypatch):
    monkeypatch.setattr(config_mod, "hosts", lambda: {
        "mac": {"os": "darwin", "agents_root": "/Users/gob/x",
                "provides": ["chrome"], "max_workers": 4},
    })

    db_mod.seed_hosts_from_config()
    # a node_agent heartbeat lands after the first seed
    db_mod.upsert_host("mac", status="online", probed_at="2026-09-29T00:00:00+00:00",
                        free_gb=10.0, ram_free_gb=3.0, running=1, version="9.9.9")

    db_mod.seed_hosts_from_config()  # rerun -- must not touch probe fields

    h = db_mod.get_host("mac")
    assert h["os"] == "darwin"
    assert h["max_workers"] == 4
    assert h["status"] == "online"
    assert h["probed_at"] == "2026-09-29T00:00:00+00:00"
    assert h["free_gb"] == 10.0
    assert h["ram_free_gb"] == 3.0
    assert h["running"] == 1
    assert h["version"] == "9.9.9"


def test_seed_hosts_from_config_never_imports_yaml_at_module_level():
    """The hard constraint: lib.db itself must stay importable without
    PyYAML -- lib.config (which requires it) is only pulled in once
    seed_hosts_from_config() actually runs. Reading the source is the most
    direct proof of that (the equivalent of tests/test_hook_guard_without_yaml
    .py, which proves the import side; this proves the call site)."""
    import inspect
    src = inspect.getsource(db_mod.seed_hosts_from_config)
    assert "from lib import config" in src
    top_of_file = inspect.getsource(db_mod).split("def create_task")[0]
    assert "from lib import config" not in top_of_file
    assert "import lib.config" not in top_of_file


# ---------------------------------------------------------------------------
# letters
# ---------------------------------------------------------------------------

def test_letter_lifecycle_create_pending_delivered():
    lid = db_mod.create_letter("contabo", "cto", "hello there",
                               from_role="cto", from_session="cto-mac1")
    assert isinstance(lid, int)

    letter = db_mod.get_letter(lid)
    assert letter["to_host"] == "contabo"
    assert letter["to_role"] == "cto"
    assert letter["from_role"] == "cto"
    assert letter["from_session"] == "cto-mac1"
    assert letter["body"] == "hello there"
    assert letter["status"] == "pending"
    assert letter["delivered_at"] is None
    assert letter["attempts"] == 0

    pending = db_mod.pending_letters("contabo")
    assert [p["id"] for p in pending] == [lid]

    assert db_mod.mark_letter_delivered(lid) is True
    delivered = db_mod.get_letter(lid)
    assert delivered["status"] == "delivered"
    assert delivered["delivered_at"]

    # delivered letters drop out of the pending queue
    assert db_mod.pending_letters("contabo") == []


def test_mark_letter_delivered_twice_is_idempotent():
    lid = db_mod.create_letter("mac", "cmo", "budget question")
    assert db_mod.mark_letter_delivered(lid) is True
    assert db_mod.mark_letter_delivered(lid) is False  # already delivered -- no error
    assert db_mod.get_letter(lid)["status"] == "delivered"


def test_mark_letter_delivered_missing_id_returns_false():
    assert db_mod.mark_letter_delivered(999999) is False


def test_pending_letters_only_targets_the_named_host():
    db_mod.create_letter("contabo", "cto", "for contabo")
    db_mod.create_letter("winbox", "cto", "for winbox")
    assert [l["to_host"] for l in db_mod.pending_letters("contabo")] == ["contabo"]
    assert [l["to_host"] for l in db_mod.pending_letters("winbox")] == ["winbox"]


def test_record_letter_attempt_five_failures_flips_to_failed():
    lid = db_mod.create_letter("winbox", "cto", "will fail to deliver")
    for i in range(4):
        db_mod.record_letter_attempt(lid, f"ssh timeout #{i}")
        letter = db_mod.get_letter(lid)
        assert letter["status"] == "pending"
        assert letter["attempts"] == i + 1

    db_mod.record_letter_attempt(lid, "ssh timeout #4")
    letter = db_mod.get_letter(lid)
    assert letter["attempts"] == 5
    assert letter["status"] == "failed"
    assert letter["last_error"] == "ssh timeout #4"


def test_record_letter_attempt_on_missing_id_does_not_raise():
    db_mod.record_letter_attempt(999999, "whatever")  # no row -- just a no-op
