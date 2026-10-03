"""Org Mesh W4.1: tools/hq_join.py -- one-time join tokens, leave, hosts export.

Every test runs against a throwaway ledger: SQLite in tmp_path by default, and
also the Postgres named by ORG_TEST_DB_URL when it is set (same convention as
tests/test_db_backend_pg.py; the pg param skips otherwise). Nothing here calls
Infisical, Tailscale, GitHub or ssh: `leave` gets fake revokers.

Run:  .venv/bin/python -m pytest tests/test_w41_hq_join.py
"""
from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
import yaml

from lib import config, db
from lib import db_pg
from tools import hq_join

# The example recipient from the age README: a real bech32 checksum.
PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
_PG_TABLES = ("locks", "events", "tasks", "c_level_sessions", "hosts", "letters", "join_tokens")


def _drop_pg(url: str) -> None:
    conn = db_pg.connect(url, timeout=10)
    try:
        for table in _PG_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(params=["sqlite", "pg"], autouse=True)
def hub(request, monkeypatch, tmp_path):
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    if request.param == "pg":
        if not ORG_TEST_DB_URL:
            pytest.skip("ORG_TEST_DB_URL not set -- pg param runs only against a throwaway org_test")
        monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
        _drop_pg(ORG_TEST_DB_URL)
        db.init()
        yield request.param
        _drop_pg(ORG_TEST_DB_URL)
    else:
        monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
        db.init()
        yield request.param


def _join(host="node-a", os_name="linux", hq_root="/opt/MoonieXHQ", pubkey=PUB, **kw):
    """mint + accept; returns (token, accept result)."""
    token = hq_join.mint(host)["token"]
    return token, hq_join.accept(token, host, os_name, hq_root, pubkey, **kw)


def _host(name):
    return db.get_host(name)


def _token_row(token):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM join_tokens WHERE token_hash=?",
                           (hq_join.hash_token(token),)).fetchone()
    return dict(row) if row else None


def _refusal(fn, *a, **kw) -> hq_join.JoinError:
    with pytest.raises(hq_join.JoinError) as ei:
        fn(*a, **kw)
    return ei.value


def _dump() -> dict:
    """Every hub table this tool can write, for before/after equality."""
    with db.get_conn() as conn:
        return {t: [dict(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall()]
                for t in ("hosts", "join_tokens", "events")}


# ---------------------------------------------------------------- schema

def _hosts_columns() -> set:
    with db.get_conn() as conn:
        return {r["name"] for r in conn.execute("PRAGMA table_info(hosts)").fetchall()}


def test_an_older_hosts_table_gains_pubkey_and_config_json_once():
    with db.get_conn() as conn:
        conn.execute("ALTER TABLE hosts DROP COLUMN pubkey")
        conn.execute("ALTER TABLE hosts DROP COLUMN config_json")
    assert not {"pubkey", "config_json"} & _hosts_columns()
    db.init()
    db.init()  # a second ADD COLUMN would raise "duplicate column name"
    assert {"pubkey", "config_json"} <= _hosts_columns()
    with db.get_conn() as conn:
        tokens = {r["name"] for r in conn.execute("PRAGMA table_info(join_tokens)").fetchall()}
    assert {"token_hash", "host", "created_at", "expires_at", "used_at"} <= tokens


# ------------------------------------------------------------------ mint

def test_mint_stores_only_the_hash():
    res = hq_join.mint("node-a")
    assert res["token"].startswith("hqj_") and len(res["token"]) == 47
    row = _token_row(res["token"])
    assert row["token_hash"] == hq_join.hash_token(res["token"])
    assert row["host"] == "node-a" and row["used_at"] is None
    assert res["token"] not in json.dumps(_dump())


def test_mint_default_ttl_is_15_minutes_and_ttl_is_bounded():
    t0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert hq_join.mint("node-a", now=t0)["expires_at"] == "2026-10-01T12:15:00+00:00"
    assert hq_join.mint("node-b", 60, now=t0)["expires_at"] == "2026-10-01T13:00:00+00:00"
    for bad in (0, -5, 61):
        assert _refusal(hq_join.mint, "node-c", bad).code == "bad_arg"


@pytest.mark.parametrize("name", ["", "a", "ab", "Node", "node_a", "node a", "-node", "node-",
                                  "x" * 32, "x" * 33, "../etc", "node\n", "n\u00f6de"])
def test_mint_refuses_bad_host_names(name):
    assert _refusal(hq_join.mint, name).code == "bad_arg"


@pytest.mark.parametrize("name", ["abc", "a1b", "node-a", "x" * 31, "a-" * 15 + "b"])
def test_mint_and_accept_take_host_names_of_3_to_31_chars(name):
    # 31 is the most `infisical_setup.py save` (NAME_RE, 2-31 chars) takes as an identity name.
    _, joined = _join(name)
    assert joined["host"] == name
    assert _host(name)["status"] == hq_join.STATUS_PENDING


@pytest.mark.parametrize("name", ["x" * 32, "a" * 40])
def test_accept_refuses_a_32_char_host_name_too(name):
    # accept checks the name before it looks at the token, so a name mint would never
    # have minted a token for is refused here with the same code and nothing written.
    before = _dump()
    err = _refusal(hq_join.accept, "hqj_" + "A" * 43, name, "linux", "/opt/MoonieXHQ", PUB)
    assert err.code == "bad_arg" and "3-31" in err.message
    assert _dump() == before


@pytest.mark.parametrize("status", ["online", "pending_identity", "offline", None])
def test_mint_refuses_a_name_that_has_a_row(status):
    db.upsert_host("node-a", os="linux", **({} if status is None else {"status": status}))
    assert _refusal(hq_join.mint, "node-a").code == "host_in_use"
    assert _dump()["join_tokens"] == []


def test_mint_refuses_a_name_declared_in_hosts_yaml_even_without_a_row(monkeypatch):
    # mac, winbox and contabo are reserved names now (W4.6a F13) and refused as bad_arg before
    # this check; a declared name that is not reserved still reaches it.
    real = config.hosts()
    monkeypatch.setattr(config, "hosts", lambda: {**real, "declared-x": {"os": "linux"}})
    assert _refusal(hq_join.mint, "declared-x").code == "host_in_use"
    for name in ("mac", "winbox", "contabo"):
        assert _refusal(hq_join.mint, name).code == "bad_arg"


def test_mint_allows_a_name_that_left():
    db.upsert_host("node-a", os="linux", status="left")
    assert hq_join.mint("node-a")["host"] == "node-a"


# ---------------------------------------------------------------- accept

def test_accept_registers_a_pending_identity_row_with_the_pubkey():
    token, res = _join("node-a", "linux", "/opt/MoonieXHQ/")
    h = _host("node-a")
    assert res == {"host": "node-a", "status": "pending_identity",
                   "agents_root": "/opt/MoonieXHQ/Agents/Core", "fingerprint": PUB[-8:]}
    assert h["approved_at"] is None     # W4.6a F1: accept approves nothing
    assert h["status"] == "pending_identity" and h["pubkey"] == PUB
    assert h["os"] == "linux" and h["hq_root"] == "/opt/MoonieXHQ"
    assert h["agents_root"] == "/opt/MoonieXHQ/Agents/Core"
    entry = json.loads(h["config_json"])
    assert entry["worktrees"] == "/opt/MoonieXHQ/Agents/Core/worktrees"
    assert entry["ssh"] == "node-a" and entry["provides"] == [] and entry["runners"] == []
    assert _token_row(token)["used_at"] is not None


def test_accept_windows_layout_uses_backslashes():
    _join("winnode", "windows", "C:\\Users\\x\\MoonieXHQ")
    entry = json.loads(_host("winnode")["config_json"])
    assert entry["agents_root"] == "C:\\Users\\x\\MoonieXHQ\\Agents\\Core"
    assert entry["worktrees"] == "C:\\Users\\x\\MoonieXHQ\\Agents\\Core\\worktrees"


def test_unknown_token_changes_nothing_and_does_not_echo_it():
    before = _dump()
    wrong = "hqj_" + "A" * 43
    err = _refusal(hq_join.accept, wrong, "node-a", "linux", "/opt/x", PUB)
    assert err.code == "unknown_token" and wrong not in err.message
    err = _refusal(hq_join.accept, "not-a-token", "node-a", "linux", "/opt/x", PUB)
    assert err.code == "unknown_token" and "not-a-token" not in err.message
    assert _dump() == before


def test_wrong_host_changes_nothing_and_the_token_still_works():
    token = hq_join.mint("node-a")["token"]
    before = _dump()
    err = _refusal(hq_join.accept, token, "node-b", "linux", "/opt/x", PUB)
    assert err.code == "wrong_host" and token not in err.message
    assert _dump() == before
    assert hq_join.accept(token, "node-a", "linux", "/opt/x", PUB)["host"] == "node-a"


def test_expired_token_is_refused_and_changes_nothing():
    t0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    token = hq_join.mint("node-a", 15, now=t0)["token"]
    before = _dump()
    for late in (t0 + timedelta(minutes=15), t0 + timedelta(hours=3)):  # the boundary counts
        err = _refusal(hq_join.accept, token, "node-a", "linux", "/opt/x", PUB, now=late)
        assert err.code == "expired" and token not in err.message
    assert _dump() == before
    ok = hq_join.accept(token, "node-a", "linux", "/opt/x", PUB, now=t0 + timedelta(minutes=14))
    assert ok["status"] == "pending_identity"


def test_reused_token_is_refused_and_the_row_is_untouched():
    token, _ = _join("node-a")
    before = _dump()
    err = _refusal(hq_join.accept, token, "node-a", "linux", "/tmp/elsewhere", PUB)
    assert err.code == "already_used" and token not in err.message
    assert _dump() == before
    assert _host("node-a")["hq_root"] == "/opt/MoonieXHQ"


def test_name_taken_between_mint_and_accept_rolls_the_consume_back():
    token = hq_join.mint("node-a")["token"]
    db.upsert_host("node-a", os="linux", status="online")  # someone got there first
    err = _refusal(hq_join.accept, token, "node-a", "linux", "/opt/x", PUB)
    assert err.code == "host_in_use"
    assert _token_row(token)["used_at"] is None
    assert _host("node-a")["status"] == "online" and _host("node-a")["pubkey"] is None


@pytest.mark.parametrize("kw,needle", [
    ({"os_name": "beos"}, "os must be"),
    ({"hq_root": "relative/path"}, "absolute"),
    ({"hq_root": "/opt/../etc"}, "'..'"),
    ({"hq_root": "/opt/x\nbad"}, "control"),
    ({"hq_root": "/"}, "root"),
    ({"os_name": "windows", "hq_root": "/opt/x"}, "absolute windows"),
    ({"pubkey": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIexample"}, "age"),
    ({"pubkey": PUB[:-1] + "q"}, "age"),       # one typo: checksum fails
    ({"pubkey": PUB.upper()}, "age"),
])
def test_bad_arguments_are_refused_before_the_token_is_spent(kw, needle):
    token = hq_join.mint("node-a")["token"]
    args = {"os_name": "linux", "hq_root": "/opt/MoonieXHQ", "pubkey": PUB, **kw}
    err = _refusal(hq_join.accept, token, "node-a", args["os_name"], args["hq_root"], args["pubkey"])
    assert err.code == "bad_arg" and needle in err.message
    assert _token_row(token)["used_at"] is None and _host("node-a") is None


def test_rejoin_after_leave_replaces_the_old_identity():
    _join("node-a", "linux", "/opt/old")
    db.upsert_host("node-a", status="left", probed_at="2026-09-01T00:00:00+00:00", free_gb=9.0)
    token = hq_join.mint("node-a")["token"]
    hq_join.accept(token, "node-a", "darwin", "/Users/x/MoonieXHQ", PUB)
    h = _host("node-a")
    assert h["status"] == "pending_identity" and h["os"] == "darwin"
    assert h["probed_at"] is None and h["free_gb"] is None


# ------------------------------------------------------ single use, raced

N_RACERS = 20


def _race(n=N_RACERS):
    token = hq_join.mint("node-a")["token"]
    start = threading.Barrier(n)

    def attempt(_):
        start.wait(timeout=30)
        try:
            hq_join.accept(token, "node-a", "linux", "/opt/MoonieXHQ", PUB)
            return "ok"
        except hq_join.JoinError as exc:
            return exc.code
        except Exception as exc:  # a crash is a result too, never a silent pass
            return f"crash:{type(exc).__name__}:{exc}"

    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(attempt, range(n)))


def _assert_one_winner_and_the_token_refused_the_rest(results):
    assert results.count("ok") == 1, results
    # The other 19 must be stopped by the token itself, not by a later guard.
    assert [r for r in results if r != "ok"] == ["already_used"] * (len(results) - 1), results


def test_token_is_single_use_under_20_concurrent_accepts():
    results = _race()
    _assert_one_winner_and_the_token_refused_the_rest(results)
    with db.get_conn() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM hosts WHERE host='node-a'").fetchone()["n"] == 1
        accepts = conn.execute("SELECT COUNT(*) AS n FROM events WHERE kind='join_accept'").fetchone()["n"]
    assert accepts == 1


def test_probe_a_read_then_write_consume_fails_the_single_winner_check(monkeypatch):
    """The guard's probe: swap the atomic UPDATE ... RETURNING for the naive
    "SELECT unused, then UPDATE". Every racer reads `unused` before any writes
    (a barrier forces it), all 20 pass the token check, and the single-winner
    assertion above must trip. If it does not, the race test proves nothing."""
    gate = threading.Barrier(N_RACERS)

    def read_then_write(conn, now_s, token_hash, host):
        row = conn.execute(
            "SELECT used_at FROM join_tokens WHERE token_hash=? AND host=? AND expires_at>?",
            (token_hash, host, now_s)).fetchone()
        if row is None or row["used_at"] is not None:
            return False
        gate.wait(timeout=30)  # everyone has seen used_at IS NULL
        conn.execute("UPDATE join_tokens SET used_at=? WHERE token_hash=?", (now_s, token_hash))
        return True

    monkeypatch.setattr(hq_join, "_consume", read_then_write)
    results = _race()
    assert results.count("already_used") != N_RACERS - 1, results
    with pytest.raises(AssertionError):
        _assert_one_winner_and_the_token_refused_the_rest(results)


# ------------------------------------------------- the token never leaks

def test_token_never_appears_in_logs_stdout_events_or_tables(capsys, caplog):
    caplog.set_level(logging.DEBUG)
    rc = hq_join.main(["mint", "--host", "node-a"])
    out = capsys.readouterr()
    assert rc == 0
    token = out.out.strip()
    assert token.startswith("hqj_") and out.out.count(token) == 1   # once, on stdout
    assert token not in out.err

    # wrong host, then the good accept, then a reuse
    for host in ("node-b", "node-a", "node-a"):
        hq_join.main(["accept", "--token", token, "--host", host, "--os", "linux",
                      "--hq-root", "/opt/x", "--pubkey", PUB])
    later = capsys.readouterr()
    assert token not in later.out and token not in later.err
    assert token not in caplog.text
    assert token not in json.dumps(_dump())
    assert any(r["kind"] == "join_mint" for r in _dump()["events"])


def test_accept_can_read_the_token_from_stdin(monkeypatch, capsys):
    import io
    token = hq_join.mint("node-a")["token"]
    monkeypatch.setattr("sys.stdin", io.StringIO(token + "\n"))
    rc = hq_join.main(["accept", "--token", "-", "--host", "node-a", "--os", "linux",
                       "--hq-root", "/opt/x", "--pubkey", PUB])
    assert rc == 0 and json.loads(capsys.readouterr().out)["status"] == "pending_identity"


def test_cli_exit_codes_refusal_is_2(capsys):
    assert hq_join.main(["mint", "--host", "BAD NAME"]) == 2
    assert "refused (bad_arg)" in capsys.readouterr().err


# ----------------------------------------------------------------- leave

class Fake:
    """A revoker table that records calls and fails the kinds it is told to."""

    def __init__(self, fail=(), boom=()):
        self.calls = []
        self.fail, self.boom = set(fail), set(boom)

    def table(self):
        def make(kind):
            def revoke(step):
                self.calls.append((step.kind, step.target))
                if kind in self.boom:
                    raise RuntimeError("provider said 500")
                return hq_join.Outcome(kind not in self.fail, "refused" if kind in self.fail else "")
            return revoke
        # No status_leaving entry: that step is the hub's own write, run inside leave() itself.
        return {k: make(k) for k in ("tailscale_device", "github_deploy_key", "authorized_keys")}


@pytest.fixture
def joined(hub):
    """A seeded core (mac, contabo, winbox) plus one joined node, online."""
    db.seed_hosts_from_config()
    _join("node-a")
    db.upsert_host("node-a", status="online")


def test_leave_without_live_prints_the_plan_and_changes_nothing(joined):
    before = _dump()
    fake = Fake()
    res = hq_join.leave("node-a", live=False, revokers=fake.table())
    assert fake.calls == [] and _dump() == before
    assert res["status"] == "planned"
    assert [s["kind"] for s in res["steps"]] == [
        "status_leaving", "tailscale_device", "github_deploy_key",
        "authorized_keys", "authorized_keys", "authorized_keys"]
    assert [s["target"] for s in res["steps"] if s["kind"] == "authorized_keys"] == \
        ["contabo", "mac", "winbox"]
    assert "token service" in res["steps"][0]["what"]      # step 1 is what stops the token at once
    assert not any("infisical" in s["kind"] for s in res["steps"])   # a node has no identity to revoke


def test_leave_cli_defaults_to_the_plan(joined, capsys):
    before = _dump()
    assert hq_join.main(["leave", "--host", "node-a"]) == 0
    assert "PLAN" in capsys.readouterr().out
    assert _dump() == before


def test_leave_full_success_marks_the_row_left(joined):
    fake = Fake()
    res = hq_join.leave("node-a", live=True, revokers=fake.table())
    assert res["status"] == "left" and res["left_behind"] == []
    assert len(fake.calls) == 5 and fake.calls[0][0] == "tailscale_device"
    assert [s["kind"] for s in res["steps"]][0] == "status_leaving" and res["steps"][0]["ok"]
    assert _host("node-a")["status"] == "left"
    assert hq_join.leave("node-a", live=True, revokers=fake.table())["note"]  # idempotent
    assert len(fake.calls) == 5


def test_leave_stops_the_token_before_any_slow_step_runs(joined):
    """The CEO's rule: a node that left can never get the token again. The row is `leaving`
    (the token service refuses it) before the first revoker is asked to do anything."""
    seen = []

    def watch(kind):
        def revoke(step):
            seen.append((kind, _host("node-a")["status"]))
            return hq_join.Outcome(True, "")
        return revoke
    table = {k: watch(k) for k in ("tailscale_device", "github_deploy_key", "authorized_keys")}
    hq_join.leave("node-a", live=True, revokers=table)
    assert seen and {status for _, status in seen} == {"leaving"}
    assert _host("node-a")["status"] == "left"


def test_leave_partial_failure_runs_every_step_and_keeps_the_row(joined):
    fake = Fake(fail={"tailscale_device"}, boom={"github_deploy_key"})
    res = hq_join.leave("node-a", live=True, revokers=fake.table())
    assert len(fake.calls) == 5                      # one failure did not stop the rest
    assert res["status"] == "partial"
    assert res["left_behind"] == ["tailscale_device:node-a", "github_deploy_key:node-a"]
    # not `left`, but already `leaving`: the token service refuses it while the rest is fixed
    assert _host("node-a")["status"] == "leaving"
    boom = next(s for s in res["steps"] if s["kind"] == "github_deploy_key")
    assert boom["ok"] is False and "RuntimeError" in boom["detail"]
    ev = [e for e in _dump()["events"] if e["kind"] == "join_leave"][-1]
    assert "provider said 500" not in ev["payload"]


def test_leave_fails_one_authorized_keys_host_and_names_it(joined):
    def flaky(step):
        return hq_join.Outcome(step.target != "mac", "ssh: timeout")
    table = {**Fake().table(), "authorized_keys": flaky}
    res = hq_join.leave("node-a", live=True, revokers=table)
    assert res["left_behind"] == ["authorized_keys:mac"] and res["status"] == "partial"


def test_leave_live_with_the_default_revokers_touches_nothing_outside(joined, capsys):
    """No revokers injected: the shipped table refuses every outside step. The hub's own first
    step still runs, so the node is `leaving` (refused by the token service), not `left`."""
    rc = hq_join.main(["leave", "--host", "node-a", "--live"])
    out = capsys.readouterr().out
    assert rc == 1 and out.count("not wired yet") == 5 and "NOT marked left" in out
    assert "[ok] status_leaving" in out
    assert _host("node-a")["status"] == "leaving"


def test_a_rerun_after_a_partial_leave_finishes_it(joined):
    hq_join.leave("node-a", live=True, revokers=Fake(fail={"tailscale_device"}).table())
    assert _host("node-a")["status"] == "leaving"
    res = hq_join.leave("node-a", live=True, revokers=Fake().table())
    assert res["status"] == "left" and _host("node-a")["status"] == "left"


def test_leave_refuses_a_host_that_never_joined_through_accept(joined):
    # mac, contabo and winbox are reserved names (W4.6a F13): refused at the name check.
    for core in ("mac", "contabo", "winbox"):
        assert _refusal(hq_join.leave, core, live=True, revokers=Fake().table()).code == "bad_arg"
    # A seeded row that never joined (no pubkey) under a name that is not reserved: not_joined.
    db.upsert_host("seeded-x", os="linux", status="online")
    assert _refusal(hq_join.leave, "seeded-x", live=True, revokers=Fake().table()).code == "not_joined"
    assert _refusal(hq_join.leave, "ghost-node").code == "unknown_host"


def test_leave_skips_hosts_that_already_left_in_the_plan(joined):
    db.upsert_host("winbox", status="left")
    targets = [s["target"] for s in hq_join.leave("node-a")["steps"] if s["kind"] == "authorized_keys"]
    assert targets == ["contabo", "mac"]


# ---------------------------------------------------------------- export

@pytest.fixture
def seeded(hub):
    db.seed_hosts_from_config()


def test_export_round_trips_what_lib_config_reads_today(seeded, tmp_path):
    current = yaml.safe_load(config.HOSTS_CONFIG.read_text(encoding="utf-8"))["hosts"]
    assert set(current) >= {"mac", "contabo", "winbox"}
    text = hq_join.export_hosts_text()
    assert text.startswith("# GENERATED")
    assert yaml.safe_load(text)["hosts"] == current == config.hosts()
    for name, entry in current.items():                    # keys keep their order too
        assert list(yaml.safe_load(text)["hosts"][name]) == list(entry)

    # and lib/config reads the export back as the same registry
    out = tmp_path / "hosts.yaml"
    assert hq_join.main(["export-hosts", "--out", str(out)]) == 0
    saved = config.HOSTS_CONFIG
    try:
        config.HOSTS_CONFIG = out
        config.hosts.cache_clear()
        assert config.hosts() == current
    finally:
        config.HOSTS_CONFIG = saved
        config.hosts.cache_clear()


def test_export_adds_a_joined_node_only_once_it_has_an_identity(seeded):
    _join("node-a")
    assert "node-a" not in yaml.safe_load(hq_join.export_hosts_text())["hosts"]   # pending
    db.upsert_host("node-a", status="online")
    entry = yaml.safe_load(hq_join.export_hosts_text())["hosts"]["node-a"]
    assert entry["os"] == "linux" and entry["ssh"] == "node-a"
    assert entry["agents_root"] == "/opt/MoonieXHQ/Agents/Core"
    db.upsert_host("node-a", status="left")
    assert "node-a" not in yaml.safe_load(hq_join.export_hosts_text())["hosts"]


def test_export_refuses_a_row_that_was_never_seeded(seeded):
    db.upsert_host("stray", os="linux", status="online")      # heartbeat row, no config_json
    err = _refusal(hq_join.export_hosts_text)
    assert err.code == "not_seeded" and "stray" in err.message


def test_export_default_is_stdout_and_never_the_tracked_file(seeded, capsys):
    before = config.HOSTS_CONFIG.read_bytes()
    assert hq_join.main(["export-hosts"]) == 0
    assert yaml.safe_load(capsys.readouterr().out)["hosts"] == config.hosts()
    assert config.HOSTS_CONFIG.read_bytes() == before
