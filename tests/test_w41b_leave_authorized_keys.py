"""Org Mesh W4.7 fix: `leave` revokes what was PLACED, so a joined node can end `left`.

Before this, the `authorized_keys` step was `not wired yet` in every mode, so every leave of
a joined node ended `partial`. join.sh / join.ps1 put a joined node's keys on the node only;
nothing writes them into another host's authorized_keys. So for a joined node the step has
nothing to remove and is ok ("none placed"). A core host's W2.8a dispatch lines ARE placed
and nothing removes them, so that step keeps refusing.

Every test runs against a throwaway ledger (SQLite in tmp_path, plus the Postgres named by
ORG_TEST_DB_URL when set, same convention as tests/test_w41_hq_join.py). Nothing here calls
Infisical, Tailscale, GitHub or ssh: the outside clients are fakes that fail the test when
they are asked for something they should never be asked.

Run:  .venv/bin/python -m pytest tests/test_w41b_leave_authorized_keys.py
"""
from __future__ import annotations

import os

import pytest

from lib import db, db_pg, tailscale_api
from tools import hq_join, infisical_setup

PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
_PG_TABLES = ("locks", "events", "tasks", "c_level_sessions", "hosts", "letters",
              "join_tokens", "node_secrets")
NONE_PLACED = "none placed"
NOT_WIRED = "not wired yet"


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
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE", hq_join.W42_FLAG):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(infisical_setup, "CRED_DIR", str(tmp_path / "no-creds"))
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


# ------------------------------------------------------------------ fakes

class FakeTailscale:
    """The tailnet client lib.tailscale_api.from_env would build."""

    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def delete_device(self, host):
        self.calls.append(host)
        if self.fail:
            raise RuntimeError("tailscale said 500")
        return True


def _no_gh(args, stdin=None):
    raise AssertionError(f"leave of a node with no deploy key recorded called gh: {args}")


def _flag_on(monkeypatch, ts):
    """ORG_W42_PROVISION=1 with every outside client faked. The node has no node_secrets row, so
    the Infisical and GitHub legs find nothing recorded: the org is never asked, gh never run."""
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setattr(hq_join, "_live_org", lambda: object())
    monkeypatch.setattr(hq_join, "_gh_subprocess", _no_gh)
    monkeypatch.setattr(tailscale_api, "from_env", lambda environ, **kw: ts)


def _ok(step):
    return hq_join.Outcome(True, "")


def _three_ok_table():
    """The wired table with the three real legs stubbed ok; authorized_keys stays the real one."""
    return {**hq_join.wired_revokers(), "infisical_client_secret": _ok,
            "tailscale_device": _ok, "github_deploy_key": _ok}


# ---------------------------------------------------------------- helpers

def _joined(host="node-a"):
    """The seeded core (mac, contabo, winbox) plus one node joined through mint + accept."""
    db.seed_hosts_from_config()
    token = hq_join.mint(host)["token"]
    hq_join.accept(token, host, "linux", "/opt/MoonieXHQ", PUB)


def _status(host):
    return db.get_host(host)["status"]


def _by_kind(res):
    out = {}
    for s in res["steps"]:
        out.setdefault(s["kind"], []).append(s)
    return out


def _hosts_table():
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM hosts ORDER BY host").fetchall()]


# ------------------------------------------------- joined node, flag on

def test_joined_node_with_the_flag_on_ends_left_and_says_none_placed(monkeypatch):
    _joined()
    ts = FakeTailscale()
    _flag_on(monkeypatch, ts)
    res = hq_join.leave("node-a", live=True)          # no revokers passed: the default table
    assert res["status"] == "left" and res["left_behind"] == []
    assert _status("node-a") == "left"
    steps = _by_kind(res)
    assert [s["ok"] for s in steps["infisical_client_secret"] + steps["tailscale_device"]
            + steps["github_deploy_key"]] == [True, True, True]
    assert ts.calls == ["node-a"]
    assert sorted(s["target"] for s in steps["authorized_keys"]) == ["contabo", "mac", "winbox"]
    for s in steps["authorized_keys"]:
        assert s["ok"] and s["detail"] == (
            f"none placed: no code puts node-a's key on {s['target']} yet "
            f"(W2.8 for joined nodes); nothing to remove")
    assert hq_join.leave("node-a", live=True)["note"] == "already left, nothing to do"


def test_the_default_table_wires_the_revoker_only_with_the_flag(monkeypatch):
    assert hq_join.default_revokers()["authorized_keys"] is hq_join.UNWIRED_REVOKERS["authorized_keys"]
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    assert hq_join.default_revokers()["authorized_keys"] is hq_join.revoke_authorized_keys


def test_a_joined_node_whose_other_steps_are_stubbed_ok_ends_left():
    """The same, through the injected-table interface the other suites use."""
    _joined()
    res = hq_join.leave("node-a", live=True, revokers=_three_ok_table())
    assert res["status"] == "left" and _status("node-a") == "left"
    assert all(NONE_PLACED in s["detail"] for s in _by_kind(res)["authorized_keys"])


def test_only_the_leaving_node_is_marked_left():
    _joined()
    before = {r["host"]: r for r in _hosts_table()}
    res = hq_join.leave("node-a", live=True, revokers=_three_ok_table())
    after = {r["host"]: r for r in _hosts_table()}
    assert res["status"] == "left"
    assert after["node-a"]["status"] == "left"
    for core in ("mac", "contabo", "winbox"):
        assert after[core]["status"] == before[core]["status"]      # the other hosts are not touched


# --------------------------------------------------- core host, flag on

def test_a_core_hosts_authorized_keys_step_keeps_refusing():
    for core in sorted(infisical_setup.MACHINES):
        step = hq_join.Step("authorized_keys", "somewhere", "remove it", core)
        out = hq_join.revoke_authorized_keys(step)
        assert out.ok is False and NOT_WIRED in out.detail and NONE_PLACED not in out.detail, core


def test_a_core_host_that_reached_leave_stays_partial(monkeypatch):
    """leave() refuses a core name at _check_host and a row with no pubkey, so this state is
    unreachable today. The branch is the second layer: if either guard is ever loosened, the
    core host's placed dispatch lines must still stop the row from going to `left`."""
    db.seed_hosts_from_config()
    db.upsert_host("winbox", pubkey=PUB)
    monkeypatch.setattr(hq_join, "_check_host", lambda host: None)
    res = hq_join.leave("winbox", live=True, revokers=_three_ok_table())
    assert res["status"] == "partial"
    assert res["left_behind"] == ["authorized_keys:contabo", "authorized_keys:mac"]
    steps = _by_kind(res)["authorized_keys"]
    assert all(not s["ok"] and NOT_WIRED in s["detail"] and NONE_PLACED not in s["detail"]
               for s in steps)
    assert _status("winbox") != "left"


# ------------------------------------------------------------- flag off

def test_flag_off_every_leg_still_refuses_and_nothing_is_marked_left():
    _joined()
    before = _hosts_table()
    res = hq_join.leave("node-a", live=True)          # no flag, no revokers: UNWIRED_REVOKERS
    assert res["status"] == "partial" and len(res["steps"]) == 6
    assert all(not s["ok"] and NOT_WIRED in s["detail"] for s in res["steps"])
    assert not any(NONE_PLACED in s["detail"] for s in res["steps"])
    assert len(res["left_behind"]) == 6
    assert _hosts_table() == before


def test_flag_off_cli_prints_six_refusals_and_does_not_mark_left(capsys):
    _joined()
    assert hq_join.main(["leave", "--host", "node-a", "--live"]) == 1
    out = capsys.readouterr().out
    assert out.count(NOT_WIRED) == 6 and "NOT marked left" in out and NONE_PLACED not in out
    assert _status("node-a") != "left"


# ------------------------------------------------------------- re-run

def test_a_rerun_after_a_partial_leave_converges_to_left(monkeypatch):
    _joined()
    ts = FakeTailscale(fail=True)
    _flag_on(monkeypatch, ts)
    first = hq_join.leave("node-a", live=True)
    assert first["status"] == "partial" and first["left_behind"] == ["tailscale_device:node-a"]
    assert all(s["ok"] for s in _by_kind(first)["authorized_keys"])    # not what held it back
    assert _status("node-a") != "left"
    ts.fail = False
    second = hq_join.leave("node-a", live=True)
    assert second["status"] == "left" and second["left_behind"] == []
    assert _status("node-a") == "left"
    assert ts.calls == ["node-a", "node-a"]


def test_a_node_left_partial_by_the_old_code_is_marked_left_by_a_rerun():
    """The row the old code left behind: every other leg went through, only authorized_keys
    refused, and the status stayed as it was."""
    _joined()
    db.upsert_host("node-a", status="online")
    old = {**_three_ok_table(), "authorized_keys": hq_join.UNWIRED_REVOKERS["authorized_keys"]}
    res = hq_join.leave("node-a", live=True, revokers=old)
    assert res["status"] == "partial" and _status("node-a") == "online"
    res = hq_join.leave("node-a", live=True, revokers=_three_ok_table())
    assert res["status"] == "left" and _status("node-a") == "left"


# ------------------------------------------- the placement guard

HOSTS = ("node-a", "mac", "contabo", "winbox", "setup", "org-node")


def test_a_joined_node_has_no_placed_lines_today():
    for target in HOSTS[1:]:
        assert hq_join._placed_authorized_keys("node-a", target) == []


def test_a_step_that_names_no_node_is_refused_not_called_none_placed():
    out = hq_join.revoke_authorized_keys(hq_join.Step("authorized_keys", "mac", "remove it"))
    assert out.ok is False and NONE_PLACED not in out.detail


def test_none_placed_is_never_reported_while_the_function_returns_a_placement(monkeypatch):
    """The guard. W2.8-for-nodes will start putting a joined node's key on other hosts. If it
    records the placement in _placed_authorized_keys but nothing removes it, the revoker must
    not go on saying "none placed": that would mark a node `left` while its key still opens
    a door."""
    step = hq_join.Step("authorized_keys", "contabo", "remove it", "node-a")
    first = hq_join.revoke_authorized_keys(step)
    assert first.ok and NONE_PLACED in first.detail                 # today: nothing placed

    line = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA" + "B" * 43 + " node-a"
    monkeypatch.setattr(hq_join, "_placed_authorized_keys", lambda host, target: [line])
    out = hq_join.revoke_authorized_keys(step)
    assert out.ok is False and NONE_PLACED not in out.detail

    _joined()
    res = hq_join.leave("node-a", live=True, revokers=_three_ok_table())
    assert res["status"] == "partial" and _status("node-a") != "left"
    assert res["left_behind"] == ["authorized_keys:contabo", "authorized_keys:mac",
                                  "authorized_keys:winbox"]


def test_the_revoker_says_none_placed_exactly_when_the_function_returns_nothing():
    for host in HOSTS:
        for target in HOSTS:
            if host == target:
                continue
            out = hq_join.revoke_authorized_keys(
                hq_join.Step("authorized_keys", target, "remove it", host))
            placed = hq_join._placed_authorized_keys(host, target)
            assert (NONE_PLACED in out.detail) == (placed == []), (host, target)
            assert out.ok == (placed == []), (host, target)


def test_plan_leave_names_the_leaving_node_on_every_authorized_keys_step():
    _joined()
    with db.get_conn() as conn:
        steps = hq_join.plan_leave(conn, "node-a")
    keys = [s for s in steps if s.kind == "authorized_keys"]
    assert len(keys) == 3 and all(s.host == "node-a" for s in keys)
    assert {s.target for s in keys} == {"mac", "contabo", "winbox"}
