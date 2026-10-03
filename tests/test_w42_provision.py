"""Org Mesh W4.2 / W4.2b: provision, sealed, wired revokers, watchdog pass.

Nothing here contacts Infisical, GitHub or a node. A node has no Infisical identity (W4.2b, CEO
2026-10-03): provision seals a v2 bundle that holds the hub's token URL, and `_no_infisical`
proves provision and leave never reach Infisical. `gh` is a fake runner (`FakeGh`) and age is a
fake sealer (`fake_seal`, reversible base64, test-only). Every test runs on a throwaway ledger:
SQLite in tmp_path, and also the Postgres named by ORG_TEST_DB_URL when set (the pg param skips
otherwise), so the node_secrets table is proven on both backends.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w42_provision.py
"""
from __future__ import annotations

import ast
import base64
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib import db, db_pg, sealed, tailscale_api
from runners import watchdog
from tools import hq_join, infisical_setup

PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
# A real ssh-keygen -t ed25519 public key. A prefix + "A" * n fixture checks the regex against itself.
DEPLOY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPevyJRWgM559TAkS0aqU6fNI/5HXCNkmC5EoKCEpoB6"
ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
_PG_TABLES = ("locks", "events", "tasks", "c_level_sessions", "hosts", "letters",
              "join_tokens", "node_secrets")
T0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
TOKEN_URL = "http://100.64.0.7:8792/v1/token"


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
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE", hq_join.W42_FLAG, hq_join.TOKEN_URL_ENV,
                tailscale_api.ID_ENV, tailscale_api.SECRET_ENV):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    # Whatever happens, this file never logs in to a real Infisical or finds a real credential file.
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

class FakeGh:
    """gh(args, stdin) -> (rc, out, err), holding the deploy keys of one repo."""

    def __init__(self, fail_hosts=(), fail_delete=False):
        self.calls, self.keys, self._id = [], {}, 4000
        self.fail_titles = {f"org-node:{h}" for h in fail_hosts}
        self.fail_delete = fail_delete
        self.on_add = None          # called right after a key is made (the tests that break a later step)

    def __call__(self, args, stdin=None):
        self.calls.append((list(args), stdin))
        repo = f"repos/{hq_join.GH_REPO}/keys"
        if args[:2] == ["api", repo] and "POST" in args:
            assert args[-2:] == ["--input", "-"], args
            body = json.loads(stdin)
            if body["title"] in self.fail_titles:
                return 1, "", "gh: Validation Failed (HTTP 422)"
            self._id += 1
            self.keys[self._id] = body
            if self.on_add:
                self.on_add()
            return 0, json.dumps({"id": self._id, "title": body["title"]}), ""
        m = re.fullmatch(re.escape(repo) + r"/(\d+)", args[1]) if args[0] == "api" else None
        if m and "DELETE" in args:
            if self.fail_delete:
                return 1, "", "gh: Server Error (HTTP 500)"
            if int(m[1]) not in self.keys:
                return 1, "", "gh: Not Found (HTTP 404)"
            del self.keys[int(m[1])]
            return 0, "", ""
        raise AssertionError(f"unexpected gh call {args}")


def _always_500(args, stdin=None):
    return 1, "", "gh: Server Error (HTTP 500)"


def fake_seal(recipient, data):
    """Test-only stand-in for age: reversible, armored, carries the recipient."""
    body = base64.b64encode(recipient.encode() + b"\n" + data)
    return sealed.ARMOR_HEADER + b"\n" + body + b"\n-----END AGE ENCRYPTED FILE-----\n"


def unseal(text):
    recipient, data = base64.b64decode(text.strip().split("\n")[1]).split(b"\n", 1)
    return recipient.decode(), json.loads(data)


# ---------------------------------------------------------------- helpers

def _join(host="node-a", deploy=DEPLOY, approve=True):
    """mint + accept, and (W4.6a F1) approve: provision skips a row nobody approved. Tests of the
    gate itself pass approve=False (tests/test_w46a_hub_fixes.py)."""
    token = hq_join.mint(host)["token"]
    res = hq_join.accept(token, host, "linux", "/opt/MoonieXHQ", PUB, deploy_pubkey=deploy)
    if approve:
        hq_join.approve(host, PUB[-8:])
    return res


def _prov(host="node-a", gh=None, **kw):
    kw.setdefault("sealer", fake_seal)
    kw.setdefault("token_url", TOKEN_URL)
    return hq_join.provision(host, gh=gh, **kw)


def _ns(host="node-a"):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM node_secrets WHERE host=?", (host,)).fetchone()
    return dict(row) if row else None


def _status(host="node-a"):
    return db.get_host(host)["status"]


def _events(kind):
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM events WHERE kind=?", (kind,)).fetchall()]


def _all_text():
    """Every hub table this code can touch, as one string."""
    out = []
    with db.get_conn() as conn:
        for t in ("hosts", "join_tokens", "events", "node_secrets", "tasks", "locks",
                  "letters", "c_level_sessions"):
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {t}").fetchall()]
            out.append(json.dumps(rows, default=str))
    return "\n".join(out)


def _refusal(fn, *a, **kw) -> hq_join.JoinError:
    with pytest.raises(hq_join.JoinError) as ei:
        fn(*a, **kw)
    return ei.value


# ---------------------------------------------------------------- the table

def test_node_secrets_table_has_the_columns_and_init_is_idempotent():
    db.init()
    db.init()
    with db.get_conn() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(node_secrets)").fetchall()}
        hosts = {r["name"] for r in conn.execute("PRAGMA table_info(hosts)").fetchall()}
    assert cols == {"host", "ciphertext", "infisical_client_secret_id", "github_deploy_key_id",
                    "created_at", "fetched_at", "revoked_at"}
    assert "deploy_pubkey" in hosts


def test_an_older_hosts_table_gains_deploy_pubkey_once():
    with db.get_conn() as conn:
        conn.execute("ALTER TABLE hosts DROP COLUMN deploy_pubkey")
    db.init()
    db.init()
    with db.get_conn() as conn:
        assert "deploy_pubkey" in {r["name"] for r in conn.execute("PRAGMA table_info(hosts)").fetchall()}


def test_the_claim_statement_places_a_row_once_and_takes_over_only_a_revoked_one():
    def claim(ts):
        with db.get_conn() as conn:
            return conn.execute(hq_join._CLAIM_SQL, ("node-a", ts)).fetchone()

    assert claim("t1") is not None and _ns()["created_at"] == "t1"
    assert claim("t2") is None and _ns()["created_at"] == "t1"            # live claim stays
    with db.get_conn() as conn:
        conn.execute("UPDATE node_secrets SET revoked_at='r', github_deploy_key_id='9' WHERE host='node-a'")
    assert claim("t3") is None                                            # revoked but a key is left
    with db.get_conn() as conn:
        conn.execute("UPDATE node_secrets SET github_deploy_key_id=NULL WHERE host='node-a'")
    assert claim("t4") is not None
    row = _ns()
    assert row["created_at"] == "t4" and row["revoked_at"] is None and row["ciphertext"] is None


# ------------------------------------------------------------ infisical_setup

def test_infisical_setup_stays_stdlib_only():
    """A Run Inbox card copies this one file: no import outside the standard library."""
    tree = ast.parse(Path(infisical_setup.__file__).read_text(encoding="utf-8"))
    mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module.split(".")[0] for n in ast.walk(tree)
             if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
    assert mods <= set(sys.stdlib_module_names), mods - set(sys.stdlib_module_names)


# ---------------------------------------------------------- accept --deploy-pubkey

def test_accept_stores_the_deploy_key_in_its_own_column_not_in_config_json():
    _join("node-a", DEPLOY + " root@node-a")
    h = db.get_host("node-a")
    assert h["deploy_pubkey"] == DEPLOY                                # comment dropped, normalised
    assert DEPLOY not in (h["config_json"] or "")                      # never leaks into the export
    assert '"deploy_key": true' in _events("join_accept")[-1]["payload"]


def test_accept_without_a_deploy_key_is_not_an_error_and_is_logged(caplog):
    caplog.set_level(logging.INFO, logger="hq_join")
    _join("node-a", deploy=None)
    assert db.get_host("node-a")["deploy_pubkey"] is None
    assert "deploy key" in caplog.text


@pytest.mark.parametrize("bad", [
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC", "ssh-ed25519 short", DEPLOY + "\nssh-ed25519 second",
    DEPLOY[:-1], PUB, DEPLOY + " bad\x01comment"])
def test_a_bad_deploy_key_is_refused_before_the_token_is_spent(bad):
    token = hq_join.mint("node-a")["token"]
    err = _refusal(hq_join.accept, token, "node-a", "linux", "/opt/x", PUB, deploy_pubkey=bad)
    assert err.code == "bad_arg"
    assert db.get_host("node-a") is None
    hq_join.accept(token, "node-a", "linux", "/opt/x", PUB)           # the token is still good


def test_accept_cli_takes_the_flag_and_says_when_it_is_missing(capsys):
    tok = hq_join.mint("node-a")["token"]
    base = ["accept", "--host", "node-a", "--os", "linux", "--hq-root", "/opt/x", "--pubkey", PUB]
    assert hq_join.main(base + ["--token", tok, "--deploy-pubkey", DEPLOY + " c"]) == 0
    assert db.get_host("node-a")["deploy_pubkey"] == DEPLOY
    assert "gets no GitHub deploy key" not in capsys.readouterr().err
    tok = hq_join.mint("node-b")["token"]
    assert hq_join.main(["accept", "--host", "node-b", "--os", "linux", "--hq-root", "/opt/x",
                         "--pubkey", PUB, "--token", tok]) == 0
    assert db.get_host("node-b")["deploy_pubkey"] is None
    assert "node-b gets no GitHub deploy key" in capsys.readouterr().err


def test_a_rejoin_replaces_the_deploy_key():
    _join()
    db.upsert_host("node-a", status="left")
    other = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ2Yd9JmF0h6Hf7L52H4qZqx93vojzjt14XnLyl0YGBp"
    _join("node-a", deploy=other)
    assert db.get_host("node-a")["deploy_pubkey"] == other


# ---------------------------------------------------------------- provision

def _no_infisical(monkeypatch):
    """Fail the test if the code logs in to Infisical or sends it any request."""
    monkeypatch.setattr(infisical_setup, "Org", lambda *a, **k: pytest.fail("logged in to Infisical"))
    monkeypatch.setattr(infisical_setup.urllib.request, "urlopen",
                        lambda *a, **k: pytest.fail("sent a request to Infisical"))


def _break_the_final_write(gh):
    """Once the deploy key exists, move the host out of pending_identity: provision's last
    transaction then matches nothing, raises, and has a deploy key to undo."""
    gh.on_add = lambda: db.upsert_host("node-a", status="online")


def test_provision_happy_path_seals_a_v2_bundle_stores_it_and_flips_the_status(monkeypatch):
    _no_infisical(monkeypatch)
    _join()
    gh = FakeGh()
    res = _prov(gh=gh, now=T0)
    assert res == {"host": "node-a", "status": "identity_ready", "changed": True, "deploy_key": True}
    assert _status() == "identity_ready"
    (kid,) = gh.keys
    row = _ns()
    assert row["github_deploy_key_id"] == str(kid) and row["infisical_client_secret_id"] is None
    assert row["revoked_at"] is None and row["fetched_at"] is None and row["created_at"]
    recipient, plain = unseal(row["ciphertext"])
    assert recipient == PUB
    assert plain == {"v": 2, "host": "node-a", "token_url": TOKEN_URL}   # an address, no credential
    assert gh.keys[kid] == {"title": "org-node:node-a", "key": DEPLOY, "read_only": True}
    assert _events("node_provisioned")


def test_provision_without_a_deploy_key_makes_none():
    _join(deploy=None)
    gh = FakeGh()
    _prov(gh=gh)
    assert gh.calls == [] and _ns()["github_deploy_key_id"] is None
    assert _status() == "identity_ready" and _ns()["ciphertext"]


def test_provision_refuses_without_the_token_url_and_claims_nothing(monkeypatch):
    _join()
    monkeypatch.delenv(hq_join.TOKEN_URL_ENV, raising=False)
    gh = FakeGh()
    for unset in (None, "", "   "):
        if unset is not None:
            monkeypatch.setenv(hq_join.TOKEN_URL_ENV, unset)
        err = _refusal(hq_join.provision, "node-a", gh=gh, sealer=fake_seal)
        assert err.code == "no_token_url" and hq_join.TOKEN_URL_ENV in err.message
    assert gh.calls == [] and _ns() is None and _status() == "pending_identity"


@pytest.mark.parametrize("bad", [
    "ftp://100.64.0.7:8792/v1/token", "http://user:pw@100.64.0.7:8792/v1/token",
    "http://100.64.0.7:8792/v1/token?host=x", "http://100.64.0.7:8792/a b", "100.64.0.7:8792",
    "http://", "http://100.64.0.7:8792/v1/token#x"])
def test_provision_refuses_a_malformed_token_url(bad):
    _join()
    gh = FakeGh()
    err = _refusal(_prov, gh=gh, token_url=bad)
    assert err.code == "bad_token_url" and gh.calls == [] and _ns() is None


def test_the_token_url_comes_from_the_environment_when_none_is_passed(monkeypatch):
    _join()
    monkeypatch.setenv(hq_join.TOKEN_URL_ENV, "http://100.101.102.103:8792/v1/token")
    hq_join.provision("node-a", gh=FakeGh(), sealer=fake_seal)
    assert unseal(_ns()["ciphertext"])[1]["token_url"] == "http://100.101.102.103:8792/v1/token"


@pytest.mark.parametrize("bad", [
    "http://hub.example.ts.net:8792/v1/token", "http://127.0.0.1:8792/v1/token", "http://10.0.0.5:8792/v1/token",
    "http://194.233.80.26:8792/v1/token", "https://100.64.0.7:8792/v1/token", "http://100.64.0.7/v1/token",
    "http://100.64.0.7:8792/other", "http://100.64.0.7.evil.example:8792/v1/token",
    "http://100.128.0.1:8792/v1/token"])
def test_provision_seals_only_a_tailnet_token_url_whatever_the_environment_says(monkeypatch, bad):
    """A hostname, a public address or a loopback one in the environment is refused as bad_token_url before
    anything is claimed or sealed: a node would not use it, and a bundle that points outside the tailnet
    would send its token request (and its host name) to whoever answers there."""
    _join()
    monkeypatch.setenv(hq_join.TOKEN_URL_ENV, bad)
    gh = FakeGh()
    err = _refusal(hq_join.provision, "node-a", gh=gh, sealer=fake_seal)
    assert err.code == "bad_token_url" and gh.calls == [] and _ns() is None
    assert "100.64.0.0/10" in err.message


def test_a_sealer_failure_makes_no_deploy_key_and_leaves_the_row_pending():
    _join()
    gh = FakeGh()

    def no_age(recipient, data):
        raise sealed.SealError("age is not installed")

    err = _refusal(_prov, gh=gh, sealer=no_age)
    assert err.code == "provision_failed" and gh.calls == []
    assert _status() == "pending_identity" and _ns() is None


def test_a_gh_failure_leaves_the_row_pending_and_drops_the_claim():
    _join()
    gh = FakeGh(fail_hosts=["node-a"])
    err = _refusal(_prov, gh=gh)
    assert err.code == "provision_failed" and gh.keys == {}
    assert _status() == "pending_identity" and _ns() is None
    assert _events("node_provision_failed")


def test_a_failure_after_the_deploy_key_removes_it():
    _join()
    gh = FakeGh()
    _break_the_final_write(gh)
    err = _refusal(_prov, gh=gh)
    assert err.code == "provision_failed" and gh.keys == {} and _ns() is None
    assert _events("node_provision_failed")


def test_when_the_key_cannot_be_deleted_the_orphan_is_named_and_kept():
    _join()
    gh = FakeGh(fail_delete=True)
    _break_the_final_write(gh)
    err = _refusal(_prov, gh=gh, now=T0)
    (kid,) = gh.keys
    row = _ns()
    assert err.code == "provision_orphans" and str(kid) in err.message
    assert row["github_deploy_key_id"] == str(kid) and row["ciphertext"] is None


def test_a_run_in_progress_blocks_a_second_one_and_a_stale_one_is_cleaned_up():
    _join()
    gh = FakeGh(fail_delete=True)
    _break_the_final_write(gh)
    _refusal(_prov, gh=gh, now=T0)
    (old,) = gh.keys
    gh.fail_delete, gh.on_add = False, None
    db.upsert_host("node-a", status="pending_identity")
    calls = len(gh.calls)

    err = _refusal(_prov, gh=gh, now=T0 + timedelta(minutes=1))
    assert err.code == "busy" and len(gh.calls) == calls                 # nothing new was made

    res = _prov(gh=gh, now=T0 + timedelta(minutes=11))
    assert res["changed"] is True and _status() == "identity_ready"
    assert old not in gh.keys and len(gh.keys) == 1                      # the leftover key was deleted


def test_provision_twice_is_a_no_op():
    _join()
    gh = FakeGh()
    first = _prov(gh=gh, now=T0)
    snap = (len(gh.calls), _ns())
    again = _prov(gh=gh, now=T0 + timedelta(hours=2), token_url=None)    # no URL needed: nothing to do
    assert again == {"host": "node-a", "status": "identity_ready", "changed": False}
    assert (len(gh.calls), _ns()) == snap
    assert first["changed"] is True and len(_events("node_provisioned")) == 1


def test_provision_refuses_the_wrong_kind_of_row():
    assert _refusal(_prov, "ghost-node", gh=FakeGh()).code == "unknown_host"
    db.seed_hosts_from_config()
    # mac is a reserved name (W4.6a F13), so it is refused at the name check; a seeded row
    # under a name that is not reserved still gets not_joined.
    assert _refusal(_prov, "mac", gh=FakeGh()).code == "bad_arg"
    db.upsert_host("seeded-x", os="linux", status="online")
    assert _refusal(_prov, "seeded-x", gh=FakeGh()).code == "not_joined"
    _join()
    for status in ("online", "left", "leaving"):
        db.upsert_host("node-a", status=status)
        err = _refusal(_prov, gh=FakeGh())
        assert err.code == "bad_status" and status in err.message


def test_a_rejoined_node_is_provisioned_afresh():
    _join()
    gh = FakeGh()
    _prov(gh=gh)
    hq_join.leave("node-a", live=True, revokers=_all_ok(gh))
    assert _status() == "left" and _ns()["revoked_at"]
    _join()                                                               # same name, new token
    res = _prov(gh=gh, now=T0 + timedelta(hours=1))
    assert res["changed"] is True and _status() == "identity_ready"
    row = _ns()
    assert row["revoked_at"] is None and row["ciphertext"] and len(gh.keys) == 1


def test_the_infisical_legs_are_gone_from_hq_join():
    assert not hasattr(hq_join, "is_admin_host") and not hasattr(hq_join, "_live_org")
    assert "infisical_client_secret" not in hq_join.UNWIRED_REVOKERS
    assert "infisical_client_secret" not in hq_join.wired_revokers(gh=FakeGh())


# --------------------------------------------------------------------- sealed

def test_sealed_prints_the_stored_ciphertext_and_stamps_fetched_at_once(capsys):
    _join()
    _prov(gh=FakeGh())
    blob = _ns()["ciphertext"]
    assert hq_join.main(["sealed", "--host", "node-a"]) == 0
    assert capsys.readouterr().out == blob.rstrip("\n") + "\n"
    first = _ns()["fetched_at"]
    assert first and len(_events("node_sealed_fetch")) == 1
    hq_join.sealed_ciphertext("node-a", now=T0 + timedelta(days=1))
    assert _ns()["fetched_at"] == first and len(_events("node_sealed_fetch")) == 1


def test_sealed_refuses_a_host_with_nothing_to_give(capsys):
    assert hq_join.main(["sealed", "--host", "ghost-node"]) == 2
    assert "not_provisioned" in capsys.readouterr().err
    _join()                                                               # pending: no ciphertext yet
    assert _refusal(hq_join.sealed_ciphertext, "node-a").code == "not_provisioned"
    gh = FakeGh()
    _prov(gh=gh)
    hq_join.leave("node-a", live=True, revokers=_all_ok(gh))
    assert _refusal(hq_join.sealed_ciphertext, "node-a").code == "not_provisioned"   # revoked


# ---------------------------------------------------- the CLI and the live gate


def test_provision_cli_is_refused_without_the_flag_and_reaches_nothing(monkeypatch, capsys):
    _no_infisical(monkeypatch)
    _join()
    monkeypatch.setenv(hq_join.TOKEN_URL_ENV, TOKEN_URL)
    assert hq_join.main(["provision", "--host", "node-a"]) == 2
    assert "not_enabled" in capsys.readouterr().err and _status() == "pending_identity"


def test_provision_cli_without_the_token_url_names_the_variable(monkeypatch, capsys):
    _join()
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.delenv(hq_join.TOKEN_URL_ENV, raising=False)
    gh = FakeGh()
    monkeypatch.setattr(hq_join, "_gh_subprocess", gh)
    assert hq_join.main(["provision", "--host", "node-a"]) == 2
    err = capsys.readouterr().err
    assert "no_token_url" in err and hq_join.TOKEN_URL_ENV in err
    assert gh.calls == [] and _status() == "pending_identity"


def test_provision_cli_with_the_flag_and_the_url_works_without_infisical(monkeypatch, capsys):
    _no_infisical(monkeypatch)
    _join()
    gh = FakeGh()
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setenv(hq_join.TOKEN_URL_ENV, TOKEN_URL)
    monkeypatch.setattr(hq_join, "_gh_subprocess", gh)
    monkeypatch.setattr(sealed, "seal", fake_seal)
    assert hq_join.main(["provision", "--host", "node-a"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["host"] == "node-a" and out["status"] == "identity_ready"
    assert unseal(_ns()["ciphertext"])[1] == {"v": 2, "host": "node-a", "token_url": TOKEN_URL}


@pytest.mark.parametrize("value", ["", "0", "true", "yes", "on", " 1"])
def test_only_the_exact_string_1_turns_the_flag_on(monkeypatch, value):
    monkeypatch.setenv(hq_join.W42_FLAG, value)
    assert hq_join.w42_enabled() is False
    assert hq_join.default_revokers() is hq_join.UNWIRED_REVOKERS
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    assert hq_join.w42_enabled() is True


# ------------------------------------------------------------- leave, wired

def _all_ok(gh):
    """The wired legs plus stand-ins for the two that stay unwired in W4.2."""
    ok = lambda step: hq_join.Outcome(True, "")          # noqa: E731
    return {**hq_join.wired_revokers(gh=gh), "tailscale_device": ok, "authorized_keys": ok}


def test_leave_live_with_wired_revokers_deletes_the_stored_key_and_ends_left(monkeypatch):
    _no_infisical(monkeypatch)
    db.seed_hosts_from_config()
    _join("node-a")
    _join("node-b")
    gh = FakeGh()
    _prov("node-a", gh=gh)
    _prov("node-b", gh=gh)
    a, b = _ns("node-a"), _ns("node-b")

    res = hq_join.leave("node-a", live=True, revokers=_all_ok(gh))
    assert res["status"] == "left" and res["left_behind"] == [] and _status("node-a") == "left"
    assert res["steps"][0]["kind"] == "status_leaving"
    # exactly this host's key, by the id that was stored:
    assert [c[0] for c in gh.calls if "DELETE" in c[0]] == [
        ["api", f"repos/{hq_join.GH_REPO}/keys/{a['github_deploy_key_id']}", "-X", "DELETE"]]
    assert list(gh.keys) == [int(b["github_deploy_key_id"])]
    row = _ns("node-a")
    assert row["revoked_at"] and row["ciphertext"] is None and row["github_deploy_key_id"] is None
    assert _ns("node-b")["ciphertext"] and _status("node-b") == "identity_ready"    # untouched
    again = hq_join.leave("node-a", live=True, revokers=_all_ok(gh))
    assert again["status"] == "left" and again["steps"] == []                       # idempotent
    assert len([c for c in gh.calls if "DELETE" in c[0]]) == 1


def test_leave_with_the_default_table_and_the_flag_runs_the_key_leg_and_stays_leaving(monkeypatch):
    db.seed_hosts_from_config()
    _join()
    gh = FakeGh()
    _prov(gh=gh)
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setattr(hq_join, "_gh_subprocess", gh)
    res = hq_join.leave("node-a", live=True)                # no revokers passed: the default table
    by_kind = {}
    for s in res["steps"]:
        by_kind.setdefault(s["kind"], []).append(s)
    assert by_kind["status_leaving"][0]["ok"] and by_kind["github_deploy_key"][0]["ok"]
    assert not by_kind["tailscale_device"][0]["ok"] and "not wired yet" in by_kind["tailscale_device"][0]["detail"]
    # nothing was placed for a joined node, so there is nothing to remove: ok, not a refusal
    assert all(s["ok"] and "none placed" in s["detail"] for s in by_kind["authorized_keys"])
    assert res["status"] == "partial" and _status() == "leaving"            # tailscale holds it back
    assert gh.keys == {}
    res = hq_join.leave("node-a", live=True)                # converges: delete again is fine
    assert res["status"] == "partial" and _status() == "leaving" and _ns()["revoked_at"]


def test_leave_without_the_flag_refuses_every_outside_step_but_the_token_door_closes():
    db.seed_hosts_from_config()
    _join()
    gh = FakeGh()
    _prov(gh=gh)
    res = hq_join.leave("node-a", live=True)
    first, *rest = res["steps"]
    assert first["kind"] == "status_leaving" and first["ok"]
    assert rest and all(not s["ok"] for s in rest)
    assert res["status"] == "partial" and _status() == "leaving"
    row = _ns()
    assert row["revoked_at"] and row["ciphertext"] is None       # the sealed bundle is void from step one
    assert row["github_deploy_key_id"] and len(gh.keys) == 1     # nothing outside was touched


def test_leaving_is_set_before_any_other_step_runs():
    db.seed_hosts_from_config()
    _join()
    _prov(gh=FakeGh())
    seen = []

    def spy(step):
        seen.append((step.kind, _status()))
        return hq_join.Outcome(True, "")

    table = {k: spy for k in ("tailscale_device", "github_deploy_key", "authorized_keys")}
    res = hq_join.leave("node-a", live=True, revokers=table)
    assert [k for k, _ in seen][0] == "tailscale_device" and len(seen) >= 3
    assert all(state == "leaving" for _, state in seen)       # never identity_ready while a step runs
    assert res["status"] == "left" and _status() == "left"


def test_a_failing_step_leaves_the_row_leaving_never_issuing():
    db.seed_hosts_from_config()
    _join()
    gh = FakeGh()
    _prov(gh=gh)

    def boom(step):
        raise RuntimeError("github is down")

    res = hq_join.leave("node-a", live=True, revokers={**_all_ok(gh), "github_deploy_key": boom})
    assert res["status"] == "partial" and "github_deploy_key:node-a" in res["left_behind"]
    assert _status() == "leaving"                             # not identity_ready, not left
    assert hq_join.leave("node-a", live=True, revokers=_all_ok(gh))["status"] == "left"


def test_a_failing_revoke_leaves_the_row_and_the_ids_for_the_next_run():
    db.seed_hosts_from_config()
    _join()
    gh = FakeGh(fail_delete=True)
    _prov(gh=gh)
    table = _all_ok(gh)
    res = hq_join.leave("node-a", live=True, revokers=table)
    assert res["status"] == "partial" and any(k.startswith("github_deploy_key") for k in res["left_behind"])
    assert _ns()["revoked_at"] and _ns()["github_deploy_key_id"]          # key id kept: not deleted
    assert _status() == "leaving"
    gh.fail_delete = False
    assert hq_join.leave("node-a", live=True, revokers=table)["status"] == "left"
    assert gh.keys == {}


def test_delete_deploy_key_treats_404_as_done_and_a_server_error_as_a_failure():
    hq_join.delete_deploy_key(FakeGh(), "123")                             # never existed: 404 -> done
    with pytest.raises(hq_join.JoinError):
        hq_join.delete_deploy_key(_always_500, "123")
    for bad in ("", "12x", "../1", None):
        assert _refusal(hq_join.delete_deploy_key, FakeGh(), bad).code == "bad_arg"


# -------------------------------------------------------------- the watchdog

def _pending(*hosts):
    for h in hosts:
        _join(h)


def _live_env(monkeypatch, gh, url=TOKEN_URL):
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    if url:
        monkeypatch.setenv(hq_join.TOKEN_URL_ENV, url)
    monkeypatch.setattr(hq_join, "_gh_subprocess", gh)
    monkeypatch.setattr(sealed, "seal", fake_seal)


def test_the_watchdog_pass_is_a_no_op_without_the_flag(monkeypatch):
    _pending("node-a")
    _no_infisical(monkeypatch)
    monkeypatch.setenv(hq_join.TOKEN_URL_ENV, TOKEN_URL)
    monkeypatch.setattr(watchdog, "_provision_retry_at", {})
    assert watchdog._provision_identities() == []
    assert _status("node-a") == "pending_identity" and _ns("node-a") is None


def test_the_watchdog_pass_provisions_every_pending_row_and_one_bad_row_stops_nobody(monkeypatch):
    _no_infisical(monkeypatch)
    _pending("node-a", "node-b", "node-c")
    db.upsert_host("node-d", os="linux", status="online")  # not pending: left alone
    gh = FakeGh(fail_hosts=["node-b"])
    _live_env(monkeypatch, gh)
    monkeypatch.setattr(watchdog, "_provision_retry_at", {})
    results = watchdog._provision_identities()
    by_host = {r["host"]: r for r in results}
    assert set(by_host) == {"node-a", "node-b", "node-c"}
    assert by_host["node-a"]["changed"] and by_host["node-c"]["changed"]
    assert "error" in by_host["node-b"]
    assert [_status(h) for h in ("node-a", "node-b", "node-c")] == [
        "identity_ready", "pending_identity", "identity_ready"]
    assert len(gh.keys) == 2


def test_the_watchdog_pass_without_the_token_url_fails_every_row_by_name(monkeypatch):
    _pending("node-a")
    _live_env(monkeypatch, FakeGh(), url=None)
    monkeypatch.setattr(watchdog, "_provision_retry_at", {})
    (res,) = watchdog._provision_identities()
    assert res == {"host": "node-a", "error": "no_token_url"}
    assert _status("node-a") == "pending_identity" and _ns("node-a") is None


def test_a_failed_host_is_left_alone_for_an_hour_then_retried(monkeypatch):
    _pending("node-b")
    gh = FakeGh(fail_hosts=["node-b"])
    _live_env(monkeypatch, gh)
    monkeypatch.setattr(watchdog, "_provision_retry_at", {})
    assert "error" in watchdog._provision_identities()[0]
    calls = len(gh.calls)
    assert watchdog._provision_identities() == []           # backing off: no second try
    assert len(gh.calls) == calls
    watchdog._provision_retry_at["node-b"] = 0              # the hour has passed
    gh.fail_titles.clear()
    assert watchdog._provision_identities()[0]["changed"] is True


def test_scan_once_runs_the_identity_pass_once(monkeypatch):
    monkeypatch.setattr(watchdog, "gc_stale_tasks", lambda: [])
    monkeypatch.setattr(watchdog, "sweep_terminal_surfaces", lambda: [])
    monkeypatch.setattr(watchdog, "_drain_disk_queue", lambda: None)
    monkeypatch.setattr(watchdog.work_watch, "watch",
                        lambda: {"alerted": [], "lungnote_filed": [], "green": []})
    calls = []
    monkeypatch.setattr(watchdog, "_provision_identities", lambda: calls.append(1) or [])
    watchdog.scan_once()
    assert calls == [1]
    monkeypatch.setattr(watchdog, "_provision_identities",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    watchdog.scan_once()                                    # an error in the pass never stops the scan
