"""Org Mesh W4.6a (task-7656a701): the hub-side fixes from the W4.6 review (task-79219f24).

  F1   approval gate: hosts.approved_at, `hq_join approve`, provision skips what is not approved
  F4   a node's client secret gets a 90-day ttl (uses stay unlimited)
  F5   Windows: icacls on the credentials directory and file, fail closed
  F8   `leave --live` ends with the secret NAMES the node could read (never a value)
  F12  node.yaml may not relabel a core box as another core host
  F13  reserved host names (setup, org-node, every machine identity)
  F14  hq_root is limited to [A-Za-z0-9 ._/\\:-]

Nothing here contacts Infisical, GitHub, Tailscale or a node: the org is FakeOrg (tests/
test_w42_provision.py), gh is FakeGh, age is fake_seal, icacls is an injected runner. Every test
runs on a throwaway ledger: SQLite in tmp_path, and also the Postgres named by ORG_TEST_DB_URL
when it is set (the pg param skips otherwise).

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w46a_hub_fixes.py
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from lib import config, db, db_pg
from runners import watchdog
from test_w42_provision import FakeGh, FakeOrg, fake_seal
from tools import hq_join, infisical_setup
from tools.infisical_setup import ApiError

# The example recipient from the age README: a real bech32 checksum.
PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
FP = PUB[-8:]
# A real ssh-keygen -t ed25519 public key. A prefix + "A" * n fixture checks the regex against itself.
DEPLOY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG9D06vH3gy5M9FVCiIgDoeYU6vNWImj359y+vMWz3Qh"
ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
_PG_TABLES = ("locks", "events", "tasks", "c_level_sessions", "hosts", "letters",
              "join_tokens", "node_secrets")
_B32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _age_key(seed: int) -> str:
    """A second valid age recipient (bech32 checksum computed here), for a key that is not PUB."""
    raw = bytes((seed * 7 + i * 13) % 256 for i in range(32))
    bits = "".join(f"{b:08b}" for b in raw) + "0000"            # 260 bits = 52 five-bit groups
    data = [int(bits[i:i + 5], 2) for i in range(0, 260, 5)]
    values = [ord(c) >> 5 for c in "age"] + [0] + [ord(c) & 31 for c in "age"]
    mod = hq_join._bech32_polymod(values + data + [0] * 6) ^ 1
    data += [(mod >> 5 * (5 - i)) & 31 for i in range(6)]
    return "age1" + "".join(_B32[d] for d in data)


OTHER = _age_key(3)
assert hq_join.valid_age_recipient(OTHER) and OTHER[-8:] != FP


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


# ---------------------------------------------------------------- helpers

def _join(host="node-a", *, approve=False, pubkey=PUB, hq_root="/opt/MoonieXHQ", os_name="linux"):
    token = hq_join.mint(host)["token"]
    res = hq_join.accept(token, host, os_name, hq_root, pubkey, deploy_pubkey=DEPLOY)
    if approve:
        hq_join.approve(host, pubkey[-8:])
    return res


def _row(host="node-a"):
    return db.get_host(host)


def _events(kind):
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM events WHERE kind=?", (kind,)).fetchall()]


def _ns(host="node-a"):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM node_secrets WHERE host=?", (host,)).fetchone()
    return dict(row) if row else None


def _refusal(fn, *a, **kw) -> hq_join.JoinError:
    with pytest.raises(hq_join.JoinError) as ei:
        fn(*a, **kw)
    return ei.value


def _live_env(monkeypatch, org, gh):
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setattr(hq_join, "is_admin_host", lambda: True)
    monkeypatch.setattr(infisical_setup, "Org", lambda *a, **k: org)
    monkeypatch.setattr(hq_join, "_gh_subprocess", gh)
    monkeypatch.setattr(hq_join.sealed, "seal", fake_seal)


# ================================================================= F1: the approval gate

def _columns():
    with db.get_conn() as conn:
        return {r["name"] for r in conn.execute("PRAGMA table_info(hosts)").fetchall()}


def test_an_older_hosts_table_gains_approved_at_once():
    with db.get_conn() as conn:
        conn.execute("ALTER TABLE hosts DROP COLUMN approved_at")
    assert "approved_at" not in _columns()
    db.init()
    db.init()   # a second ADD COLUMN would raise "duplicate column name"
    assert "approved_at" in _columns()


def test_accept_approves_nothing_and_returns_the_fingerprint():
    res = _join()
    assert res["fingerprint"] == FP and len(FP) == 8
    assert _row()["approved_at"] is None and _row()["status"] == "pending_identity"


def test_approve_marks_the_row_and_logs_one_event():
    _join()
    res = hq_join.approve("node-a", FP)
    assert res["changed"] is True and res["status"] == "pending_identity"
    assert _row()["approved_at"] == res["approved_at"]
    (event,) = _events("join_approve")
    assert json.loads(event["payload"]) == {"host": "node-a", "fingerprint": FP}


def test_approve_takes_the_fingerprint_in_any_case_with_spaces_around_it():
    _join()
    assert hq_join.approve("node-a", f"  {FP.upper()}\n")["changed"] is True


def test_approving_twice_is_a_no_op_with_one_event():
    _join()
    first = hq_join.approve("node-a", FP)
    again = hq_join.approve("node-a", FP)
    assert again["changed"] is False and again["approved_at"] == first["approved_at"]
    assert len(_events("join_approve")) == 1


def test_a_wrong_fingerprint_is_refused_and_does_not_echo_the_stored_one():
    _join()
    err = _refusal(hq_join.approve, "node-a", OTHER[-8:])
    assert err.code == "fingerprint_mismatch"
    assert FP not in err.message and PUB not in err.message
    assert _row()["approved_at"] is None and _events("join_approve") == []


@pytest.mark.parametrize("bad", ["", "short", "x" * 9, "bbbbbbbb", "1111iiii", "ab cd ef"])
def test_a_malformed_fingerprint_is_refused_before_the_row_is_read(bad):
    _join()
    assert _refusal(hq_join.approve, "node-a", bad).code == "bad_arg"
    assert _row()["approved_at"] is None


def test_approve_refuses_unknown_unjoined_and_not_pending_rows():
    assert _refusal(hq_join.approve, "ghost-node", FP).code == "unknown_host"
    db.upsert_host("seeded-x", os="linux", status="online")            # no pubkey: never joined
    assert _refusal(hq_join.approve, "seeded-x", FP).code == "not_joined"
    _join()
    for status in ("identity_ready", "online", "left"):
        db.upsert_host("node-a", status=status)
        err = _refusal(hq_join.approve, "node-a", FP)
        assert err.code == "bad_status" and status in err.message
    assert _row()["approved_at"] is None


def test_the_compare_is_constant_time(monkeypatch):
    seen = []
    real = hq_join.hmac.compare_digest
    monkeypatch.setattr(hq_join.hmac, "compare_digest",
                        lambda a, b: seen.append((a, b)) or real(a, b))
    _join()
    hq_join.approve("node-a", FP)
    assert seen == [(FP.encode(), FP.encode())]


def test_a_rejoin_starts_unapproved_again():
    _join(approve=True)
    assert _row()["approved_at"] is not None
    db.upsert_host("node-a", status="left")
    _join(pubkey=OTHER)                                   # same name, new token, new key
    row = _row()
    assert row["status"] == "pending_identity" and row["approved_at"] is None
    assert row["pubkey"] == OTHER
    assert _refusal(hq_join.approve, "node-a", FP).code == "fingerprint_mismatch"   # the old one
    assert hq_join.approve("node-a", OTHER[-8:])["changed"] is True


def test_provision_refuses_an_unapproved_row_before_any_login_or_mint():
    _join()
    org, gh = FakeOrg(), FakeGh()
    err = _refusal(hq_join.provision, "node-a", org=org, gh=gh, sealer=fake_seal)
    assert err.code == "not_approved" and "hq_join approve" in err.message
    assert org.calls == [] and org.minted_values == [] and gh.calls == []
    assert _ns() is None and _row()["status"] == "pending_identity"
    hq_join.approve("node-a", FP)
    assert hq_join.provision("node-a", org=org, gh=gh, sealer=fake_seal)["changed"] is True


def test_provision_pending_skips_the_unapproved_row_and_provisions_the_rest():
    _join("node-a")
    _join("node-b", approve=True, pubkey=OTHER)
    org, gh = FakeOrg(), FakeGh()
    results = hq_join.provision_pending(org=org, gh=gh, sealer=fake_seal)
    by_host = {r["host"]: r for r in results}
    assert by_host["node-a"] == {"host": "node-a", "skipped": "not_approved"}
    assert by_host["node-b"]["changed"] is True
    assert _row("node-a")["status"] == "pending_identity" and _row("node-b")["status"] == "identity_ready"
    assert len(org.live()) == 1 and len(gh.keys) == 1


def test_provision_pending_logs_nothing_for_an_unapproved_row(caplog):
    _join()
    with caplog.at_level("DEBUG"):
        hq_join.provision_pending(org=FakeOrg(), gh=FakeGh(), sealer=fake_seal)
    assert "node-a" not in caplog.text


# --- the watchdog pass: one line per row per window, not per scan

def _watchdog(monkeypatch):
    lines = []
    monkeypatch.setattr(watchdog, "warn", lines.append)
    monkeypatch.setattr(watchdog, "_provision_retry_at", {})
    monkeypatch.setattr(watchdog, "_unapproved_noted_until", {})
    org, gh = FakeOrg(), FakeGh()
    _live_env(monkeypatch, org, gh)
    return lines, org, gh


def test_the_watchdog_says_so_once_per_window_for_an_unapproved_row(monkeypatch):
    lines, org, gh = _watchdog(monkeypatch)
    _join()
    for _ in range(4):
        results = watchdog._provision_identities()
        assert results == [{"host": "node-a", "skipped": "not_approved"}]
    assert len(lines) == 1 and "node-a" in lines[0] and "NOT approved" in lines[0]
    assert org.calls == [] and watchdog._provision_retry_at == {}     # no failure back-off
    watchdog._unapproved_noted_until["node-a"] = 0                    # the window has passed
    watchdog._provision_identities()
    assert len(lines) == 2


def test_approving_takes_effect_on_the_next_pass_with_no_back_off(monkeypatch):
    lines, org, gh = _watchdog(monkeypatch)
    _join()
    watchdog._provision_identities()
    assert "node-a" in watchdog._unapproved_noted_until
    hq_join.approve("node-a", FP)
    (res,) = watchdog._provision_identities()
    assert res["changed"] is True and _row()["status"] == "identity_ready"
    assert watchdog._unapproved_noted_until == {}                     # pruned: not waiting any more


def test_each_unapproved_row_gets_its_own_line(monkeypatch):
    lines, *_ = _watchdog(monkeypatch)
    _join("node-a")
    _join("node-b", pubkey=OTHER)
    watchdog._provision_identities()
    watchdog._provision_identities()
    assert len(lines) == 2
    assert any("node-a" in s for s in lines) and any("node-b" in s for s in lines)


# --- what the operator sees

def test_node_status_lists_joined_rows_with_the_fingerprint_and_nothing_secret():
    db.seed_hosts_from_config()                       # mac, contabo, winbox: no pubkey, not listed
    _join("node-a")
    _join("node-b", approve=True, pubkey=OTHER)
    rows = hq_join.node_status()
    assert [r["host"] for r in rows] == ["node-a", "node-b"]
    a, b = rows
    assert a["fingerprint"] == FP and a["awaiting_approval"] is True and a["approved_at"] is None
    assert b["fingerprint"] == OTHER[-8:] and b["awaiting_approval"] is False and b["approved_at"]
    assert set(a) == {"host", "status", "os", "fingerprint", "approved_at", "awaiting_approval"}
    assert [r["host"] for r in hq_join.node_status("node-b")] == ["node-b"]
    assert _refusal(hq_join.node_status, "ghost-node").code == "unknown_host"


def test_status_cli_prints_the_fingerprint_and_awaiting_approval(capsys):
    _join("node-a")
    assert hq_join.main(["status"]) == 0
    out = capsys.readouterr().out
    assert f"node-a  pending_identity  linux  fingerprint {FP}  AWAITING APPROVAL" in out
    assert PUB not in out and "approve --host" in out


def test_status_cli_with_nothing_joined_says_so(capsys):
    assert hq_join.main(["status"]) == 0
    assert "no node has joined" in capsys.readouterr().out


def test_approve_cli_prints_json_and_refuses_a_wrong_fingerprint(capsys):
    _join("node-a")
    assert hq_join.main(["approve", "--host", "node-a", "--fingerprint", OTHER[-8:]]) == 2
    captured = capsys.readouterr()
    assert "fingerprint_mismatch" in captured.err and FP not in captured.err + captured.out
    assert hq_join.main(["approve", "--host", "node-a", "--fingerprint", FP]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["changed"] is True
    hq_join.main(["status"])
    assert "approved 20" in capsys.readouterr().out                   # "approved <iso date>"


# ================================================================= F13: reserved names

RESERVED = sorted({"setup", "org-node", *infisical_setup.MACHINES})


def test_the_reserved_set_is_setup_org_node_and_every_machine():
    assert hq_join.reserved_hosts() == frozenset({"setup", "org-node", "mac", "contabo", "winbox"}
                                                 | set(infisical_setup.MACHINES))
    assert infisical_setup.SETUP == "setup" and infisical_setup.NODE_IDENTITY == "org-node"
    for name in RESERVED:     # each is otherwise a valid host name: the reserved rule is what stops it
        assert hq_join.HOST_RE.fullmatch(name), name


@pytest.mark.parametrize("name", RESERVED)
def test_every_verb_refuses_a_reserved_name(name):
    tok = hq_join.mint("node-a")["token"]
    for call in (lambda: hq_join.mint(name),
                 lambda: hq_join.accept(tok, name, "linux", "/opt/MoonieXHQ", PUB),
                 lambda: hq_join.approve(name, FP),
                 lambda: hq_join.provision(name, org=FakeOrg(), gh=FakeGh(), sealer=fake_seal),
                 lambda: hq_join.leave(name),
                 lambda: hq_join.node_status(name)):
        err = _refusal(call)
        assert err.code == "bad_arg" and "reserved" in err.message
    assert db.get_host(name) is None
    # the token was not spent by the refusals above
    assert hq_join.accept(tok, "node-a", "linux", "/opt/MoonieXHQ", PUB)["host"] == "node-a"


def test_a_name_that_only_contains_a_reserved_name_is_fine():
    for name in ("setup-2", "my-setup", "org-node2", "mac-mini", "winbox2"):
        assert hq_join.mint(name)["host"] == name


# ================================================================= F14: hq_root characters

GOOD_ROOTS = [("linux", "/opt/MoonieXHQ"), ("linux", "/opt/Moonie X_1.2-b/"),
              ("darwin", "/Users/x/MoonieXHQ"), ("windows", "C:\\Users\\x\\MoonieXHQ"),
              ("windows", "D:/Program Files/Moonie_X-1.2")]
BAD_ROOTS = [("linux", "/opt/$HOME"), ("linux", "/opt/`id`"), ("linux", "/opt/$(id)"),
             ("linux", "/opt/a;b"), ("linux", "/opt/a'b"), ("linux", '/opt/a"b'),
             ("linux", "/opt/a(b)"), ("linux", "/opt/a&b"), ("linux", "/opt/a|b"),
             ("linux", "/opt/a>b"), ("linux", "/opt/a*b"), ("linux", "/opt/a?b"),
             ("linux", "/opt/a#b"), ("linux", "/opt/a!b"), ("linux", "/opt/a%b"),
             ("linux", "/opt/\u0e44\u0e17\u0e22"), ("linux", "/opt/caf\u00e9"),
             ("windows", "C:\\Users\\x (2)\\MoonieXHQ"), ("windows", "C:\\Users\\x~1")]


@pytest.mark.parametrize("os_name,root", GOOD_ROOTS)
def test_accept_takes_a_plain_hq_root(os_name, root):
    _join(hq_root=root, os_name=os_name)
    assert _row()["hq_root"] == root.rstrip("\\/")


@pytest.mark.parametrize("os_name,root", BAD_ROOTS)
def test_accept_refuses_a_hq_root_a_shell_would_interpolate(os_name, root):
    token = hq_join.mint("node-a")["token"]
    err = _refusal(hq_join.accept, token, "node-a", os_name, root, PUB)
    assert err.code == "bad_arg"
    assert db.get_host("node-a") is None
    # a typo must not cost the token: the same token still works with a clean root
    assert hq_join.accept(token, "node-a", "linux", "/opt/MoonieXHQ", PUB)["host"] == "node-a"


@pytest.mark.parametrize("os_name,root", GOOD_ROOTS + BAD_ROOTS)
def test_lib_config_applies_the_same_hq_root_rule(os_name, root):
    try:
        want = hq_join._check_hq_root(os_name, root)
    except hq_join.JoinError:
        want = None
    assert config._node_hq_root(os_name, root) == want


# ================================================================= F12: node.yaml vs checkout path

@pytest.fixture()
def node_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ORG_HOST", raising=False)
    monkeypatch.setattr(config, "NODE_CONFIG_PATH", tmp_path / "node.yaml")
    config.self_host.cache_clear()
    config.hosts.cache_clear()
    yield tmp_path
    config.self_host.cache_clear()
    config.hosts.cache_clear()


def _node_yaml(data):
    config.NODE_CONFIG_PATH.write_text(yaml.safe_dump(data), encoding="utf-8")
    config.self_host.cache_clear()
    config.hosts.cache_clear()


def test_a_node_yaml_that_disagrees_with_the_checkout_path_is_refused(node_home, monkeypatch):
    monkeypatch.setattr(config, "_root_match_host", lambda: "mac")
    _node_yaml({"host": "contabo"})
    with pytest.raises(ValueError) as ei:
        config.self_host()
    msg = str(ei.value)
    assert "contabo" in msg and "mac" in msg and "node.yaml" in msg and "remove" in msg


def test_a_node_yaml_that_agrees_with_the_checkout_path_works(node_home, monkeypatch):
    monkeypatch.setattr(config, "_root_match_host", lambda: "mac")
    _node_yaml({"host": "mac"})
    assert config.self_host() == "mac"


def test_a_node_yaml_for_a_declared_host_works_when_the_checkout_matches_none(node_home, monkeypatch):
    monkeypatch.setattr(config, "_root_match_host", lambda: None)
    _node_yaml({"host": "winbox"})
    assert config.self_host() == "winbox"


def test_a_joined_node_keeps_working_wherever_the_checkout_is(node_home, monkeypatch):
    monkeypatch.setattr(config, "_root_match_host", lambda: "mac")
    _node_yaml({"host": "node-a", "os": "linux", "hq_root": "/opt/MoonieXHQ"})
    assert config.self_host() == "node-a"
    assert config.hosts()["node-a"]["hq_root"] == "/opt/MoonieXHQ"


def test_the_check_is_the_real_root_match_when_it_is_not_patched(node_home, monkeypatch):
    """No stub: ROOT is set to a host's agents_root and node.yaml names another declared host."""
    monkeypatch.setattr(config, "ROOT", Path(config.hosts()["contabo"]["agents_root"]))
    _node_yaml({"host": "winbox"})
    with pytest.raises(ValueError, match="agents_root of 'contabo'"):
        config.self_host()


# ================================================================= F8: rotate what the node could read

class SecretsOrg(FakeOrg):
    """FakeOrg plus the project, environment and secret-list routes node_readable_secret_names
    uses. The list answers with VALUES too, as Infisical does: none may reach the output."""

    # W4.6c F2: proj-1 is Org-Node, prod only, one secret.
    VALUES = {"prod": {"CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-LEAKME-prod"}}

    def get(self, route, **query):
        if route == "/api/v1/projects/proj-1":
            self.calls.append(("GET", route, None))
            return {"project": {"environments": [{"slug": "prod", "id": "e2"}]}}
        if route == "/api/v3/secrets/raw":
            self.calls.append(("GET", route, None))
            assert query["workspaceId"] == "proj-1" and query["secretPath"] == "/"
            return {"secrets": [{"secretKey": k, "secretValue": v}
                                for k, v in self.VALUES[query["environment"]].items()]}
        return super().get(route, **query)


def test_node_readable_secret_names_returns_names_only():
    out = infisical_setup.node_readable_secret_names(SecretsOrg())
    assert out == {"Org-Node/prod": ["CLAUDE_CODE_OAUTH_TOKEN"]}
    assert "LEAKME" not in json.dumps(out)


def test_rotate_scope_with_an_org_lists_names_and_says_where_they_came_from():
    scope = hq_join.rotate_scope(SecretsOrg())
    assert scope["source"] == "infisical" and "Org-Node/prod" in scope["names"]


def test_rotate_scope_falls_back_to_the_documented_set_and_says_why():
    none = hq_join.rotate_scope(None)
    assert none["source"] == "documented" and "no admin login" in none["why"]
    (names,) = none["names"].values()
    assert names == list(hq_join.DOCUMENTED_READABLE) == ["CLAUDE_CODE_OAUTH_TOKEN (shared by every node)"]

    class Broken(SecretsOrg):
        def get(self, route, **query):
            if route == "/api/v3/secrets/raw":
                raise ApiError("GET /api/v3/secrets/raw -> HTTP 503: LEAKME")
            return super().get(route, **query)

    failed = hq_join.rotate_scope(Broken())
    assert failed["source"] == "documented" and "lookup failed" in failed["why"]
    assert "LEAKME" not in json.dumps(failed)        # the type is named, the body is not


def _leave_table(org, gh):
    ok = lambda step: hq_join.Outcome(True, "")      # noqa: E731
    return {**hq_join.wired_revokers(org=org, gh=gh), "tailscale_device": ok, "authorized_keys": ok}


def _provisioned(monkeypatch, org, gh):
    _live_env(monkeypatch, org, gh)
    _join(approve=True)
    hq_join.provision("node-a", org=org, gh=gh, sealer=fake_seal)


def test_leave_live_ends_with_the_documented_block_when_there_is_no_admin_login(monkeypatch, capsys):
    org, gh = FakeOrg(), FakeGh()
    _provisioned(monkeypatch, org, gh)
    monkeypatch.delenv(hq_join.W42_FLAG)                   # the admin lane is off on this box
    monkeypatch.setattr(hq_join, "default_revokers", lambda: _leave_table(org, gh))
    assert hq_join.main(["leave", "--host", "node-a", "--live"]) == 0
    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    assert "ROTATE what node-a could read" in out
    assert lines[-1].strip().startswith("procedure:") and "hq-join.md" in lines[-1]
    assert "DOCUMENTED set, not read from Infisical" in out
    for item in hq_join.DOCUMENTED_READABLE:
        assert item in out
    assert out.index("is now `left`") < out.index("ROTATE")


def test_leave_live_prints_secret_names_from_infisical_and_never_a_value(monkeypatch, capsys):
    org, gh = SecretsOrg(), FakeGh()
    _provisioned(monkeypatch, org, gh)
    monkeypatch.setattr(hq_join, "default_revokers", lambda: _leave_table(org, gh))
    assert hq_join.main(["leave", "--host", "node-a", "--live"]) == 0
    captured = capsys.readouterr()
    out = captured.out
    assert "source: Infisical" in out
    assert "Org-Node/prod: CLAUDE_CODE_OAUTH_TOKEN" in out
    assert "Agents-Core" not in out
    everything = out + captured.err
    assert "LEAKME" not in everything
    assert org.minted_values[0] not in everything


def test_a_failed_leave_still_ends_with_the_block(monkeypatch, capsys):
    org, gh = FakeOrg(), FakeGh()
    db.seed_hosts_from_config()                            # the other hosts: authorized_keys steps
    _provisioned(monkeypatch, org, gh)
    monkeypatch.delenv(hq_join.W42_FLAG)
    table = _leave_table(org, gh)
    table["authorized_keys"] = lambda step: hq_join.Outcome(False, "ssh refused")
    monkeypatch.setattr(hq_join, "default_revokers", lambda: table)
    assert hq_join.main(["leave", "--host", "node-a", "--live"]) == 1
    out = capsys.readouterr().out
    assert "NOT marked left" in out and out.strip().splitlines()[-1].strip().startswith("procedure:")


def test_a_dry_run_and_an_already_left_host_print_no_rotate_block(monkeypatch, capsys):
    org, gh = FakeOrg(), FakeGh()
    _provisioned(monkeypatch, org, gh)
    assert hq_join.main(["leave", "--host", "node-a"]) == 0               # no --live
    assert "ROTATE" not in capsys.readouterr().out
    monkeypatch.setattr(hq_join, "default_revokers", lambda: _leave_table(org, gh))
    assert hq_join.main(["leave", "--host", "node-a", "--live"]) == 0
    capsys.readouterr()
    assert hq_join.main(["leave", "--host", "node-a", "--live"]) == 0     # again: nothing to do
    assert "ROTATE" not in capsys.readouterr().out


def test_hq_join_docs_carry_the_rotate_procedure_and_every_documented_category():
    doc = (Path(hq_join.__file__).resolve().parent.parent / "docs" / "ops" / "hq-join.md").read_text(
        encoding="utf-8")
    assert "After a leave: rotate what the node could read" in doc
    for needle in ("ORG_DB_URL", "CLAUDE_CODE_OAUTH_TOKEN", "Run Inbox", "SomPong", "Jules",
                   "Drive", "LungNote"):
        assert needle in doc, needle


# ================================================================= F5: icacls on Windows

def _windows(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "_is_nt", lambda: True)
    monkeypatch.setattr(infisical_setup, "require_root", lambda: None)
    monkeypatch.setattr(infisical_setup, "CRED_DIR", str(tmp_path / "creds"))


def _expected(path):
    return ["icacls", str(path), "/inheritance:r", "/grant:r", "SYSTEM:F", "Administrators:F"]


def test_lock_acl_runs_icacls_with_an_argv_list_on_nt(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "_is_nt", lambda: True)
    calls = []
    infisical_setup.lock_acl(str(tmp_path / "x"), lambda argv: calls.append(argv) or 0)
    assert calls == [_expected(tmp_path / "x")]


def test_lock_acl_does_nothing_off_windows(tmp_path):
    assert os.name != "nt"
    infisical_setup.lock_acl(str(tmp_path), lambda argv: pytest.fail("icacls ran off windows"))


def test_lock_acl_fails_closed_on_a_nonzero_exit_or_a_missing_icacls(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "_is_nt", lambda: True)
    with pytest.raises(infisical_setup.AclError, match="exited 5"):
        infisical_setup.lock_acl(str(tmp_path), lambda argv: 5)

    def missing(argv):
        raise FileNotFoundError("icacls")

    with pytest.raises(infisical_setup.AclError, match="could not run"):
        infisical_setup.lock_acl(str(tmp_path), missing)


def test_the_real_runner_uses_an_argv_list_and_no_shell(monkeypatch, tmp_path):
    seen = {}

    def fake_run(argv, **kw):
        seen["argv"], seen["kw"] = argv, kw
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(infisical_setup.subprocess, "run", fake_run)
    assert infisical_setup._run_icacls(_expected(tmp_path)) == 0
    assert isinstance(seen["argv"], list) and not seen["kw"].get("shell")


def test_write_cred_locks_the_directory_then_the_file_before_the_secret_is_final(monkeypatch, tmp_path):
    _windows(monkeypatch, tmp_path)
    creds = Path(infisical_setup.CRED_DIR)
    order = []

    def run(argv):
        target = Path(argv[1])
        order.append((argv, target.is_dir(), target.exists(), (creds / "org-node.env").exists()))
        return 0

    path = infisical_setup.write_cred("org-node", "cid", "SECRET-VALUE-1", run=run)
    (dir_argv, dir_is_dir, _, _), (file_argv, _, file_existed, final_existed) = order
    assert dir_argv == _expected(creds) and dir_is_dir
    assert file_argv == _expected(str(Path(path)) + ".tmp") and file_existed
    assert not final_existed                       # the final name appears only after the lock
    assert Path(path).read_text().count("SECRET-VALUE-1") == 1
    assert not Path(path + ".tmp").exists()


def test_write_cred_fails_closed_when_the_directory_cannot_be_locked(monkeypatch, tmp_path):
    _windows(monkeypatch, tmp_path)
    with pytest.raises(infisical_setup.AclError):
        infisical_setup.write_cred("org-node", "cid", "SECRET-VALUE-2", run=lambda argv: 1)
    assert list(Path(infisical_setup.CRED_DIR).iterdir()) == []       # no file, not even a .tmp


def test_write_cred_fails_closed_when_the_file_cannot_be_locked(monkeypatch, tmp_path):
    _windows(monkeypatch, tmp_path)
    calls = []

    def run(argv):
        calls.append(argv[1])
        return 0 if len(calls) == 1 else 1     # the directory passes, the file does not

    with pytest.raises(infisical_setup.AclError):
        infisical_setup.write_cred("org-node", "cid", "SECRET-VALUE-3", run=run)
    assert list(Path(infisical_setup.CRED_DIR).iterdir()) == []       # the .tmp that held it is gone


def test_write_cred_off_windows_calls_no_icacls(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "require_root", lambda: None)
    monkeypatch.setattr(infisical_setup, "CRED_DIR", str(tmp_path / "creds"))
    path = infisical_setup.write_cred("org-node", "cid", "SECRET-VALUE-4",
                                      run=lambda argv: pytest.fail("icacls ran off windows"))
    assert oct(os.stat(path).st_mode & 0o777) == "0o600"


def test_infisical_setup_still_imports_only_the_standard_library():
    tree = ast.parse(Path(infisical_setup.__file__).read_text(encoding="utf-8"))
    mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module.split(".")[0] for n in ast.walk(tree)
             if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
    assert mods <= set(sys.stdlib_module_names), mods - set(sys.stdlib_module_names)


# ================================================================= F4: the node secret expires

def test_the_node_secret_gets_a_90_day_ttl_and_unlimited_uses():
    assert infisical_setup.NODE_SECRET_TTL == 90 * 86_400 == 7_776_000
    org = FakeOrg()
    infisical_setup.ensure_node_identity(org)       # the identity exists; only the mint is measured
    org.calls.clear()
    out = infisical_setup.mint_node_secret(org, "node-a")
    assert org.secrets[out["client_secret_id"]]["ttl"] == 7_776_000
    assert org.secrets[out["client_secret_id"]]["uses"] == 0
    writes = [c for c in org.calls if c[0] != "GET"]
    assert len(writes) == 1                        # the identity's own settings are not touched
    method, route, body = writes[0]
    assert method == "POST" and route.endswith("/client-secrets")
    assert set(body) == {"description", "ttl", "numUsesLimit"} and body["numUsesLimit"] == 0
