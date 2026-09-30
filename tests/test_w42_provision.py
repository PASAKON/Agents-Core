"""Org Mesh W4.2: per-node identity -- provision, sealed, wired revokers, watchdog pass.

Nothing here contacts Infisical, GitHub or a node. The Infisical org is a fake
(`FakeOrg`, a subclass of infisical_setup.Org that answers the real routes from
memory), `gh` is a fake runner (`FakeGh`) and age is a fake sealer (`fake_seal`,
reversible base64, test-only). Every test runs on a throwaway ledger: SQLite in
tmp_path, and also the Postgres named by ORG_TEST_DB_URL when set (the pg param
skips otherwise), so the node_secrets table is proven on both backends.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w42_provision.py
"""
from __future__ import annotations

import ast
import base64
import json
import logging
import os
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib import db, db_pg, sealed
from runners import watchdog
from tools import hq_join, infisical_setup
from tools.infisical_setup import ApiError

PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
DEPLOY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA" + "B" * 43
ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
_PG_TABLES = ("locks", "events", "tasks", "c_level_sessions", "hosts", "letters",
              "join_tokens", "node_secrets")
T0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
UA = "/api/v1/auth/universal-auth"


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
    # Whatever happens, this file never logs in to a real Infisical or finds a real admin file.
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

class FakeOrg(infisical_setup.Org):
    """An Infisical org in memory. Org.__init__ (the login) is bypassed; the real
    identities() / projects() / identity_members() run on top of get()."""

    def __init__(self, idents=("mac", "contabo", "winbox", "setup"), *, fail_revoke=False):
        self.identity, self.token, self.org_id, self.setup_identity = "setup", "tok", "org-1", "id-setup"
        self.ids = {n: f"id-{n}" for n in idents}
        self.ua = {i: f"client-{n}" for n, i in self.ids.items()}
        self.members = {n: ["viewer"] for n in idents if n != "setup"}
        self.secrets = {}           # client secret id -> {description, revoked, ttl, uses}
        self.minted_values = []     # every secret value this org ever handed out
        self.calls = []             # (method, route, body)
        self.fail_revoke = fail_revoke
        self._n = 0

    def _uuid(self):
        self._n += 1
        return f"00000000-0000-4000-8000-{self._n:012d}"

    def live(self):
        return [k for k, v in self.secrets.items() if not v["revoked"]]

    def revoke_routes(self):
        return [r for _, r, _ in self.calls if r.endswith("/revoke")]

    def get(self, route, **query):
        self.calls.append(("GET", route, None))
        if route == "/api/v1/identities":
            return {"identities": [{"identity": {"name": n, "id": i}} for n, i in self.ids.items()]}
        if route == "/api/v2/organizations/org-1/workspaces":
            return {"workspaces": [{"slug": "agents-core", "id": "proj-1"}]}
        if route == "/api/v1/projects/proj-1/identity-memberships":
            return {"identityMemberships": [
                {"identity": {"name": n}, "roles": [{"role": r} for r in roles]}
                for n, roles in self.members.items()]}
        m = re.fullmatch(UA + r"/identities/([^/]+)", route)
        if m:
            if m[1] not in self.ua:
                raise ApiError(f"GET {route} -> HTTP 404: universal auth not configured")
            return {"identityUniversalAuth": {"clientId": self.ua[m[1]]}}
        m = re.fullmatch(UA + r"/identities/([^/]+)/client-secrets", route)
        if m:
            return {"clientSecretData": [
                {"id": k, "description": v["description"], "createdAt": "2026-10-01T00:00:00Z",
                 "isClientSecretRevoked": v["revoked"]} for k, v in self.secrets.items()]}
        raise AssertionError(f"unexpected GET {route}")

    def send(self, method, route, body=None, **query):
        self.calls.append((method, route, body))
        if (method, route) == ("POST", "/api/v1/identities"):
            iid = f"id-{body['name']}"
            self.ids[body["name"]] = iid
            return {"identity": {"id": iid}}
        m = re.fullmatch(UA + r"/identities/([^/]+)", route)
        if m and method == "POST":
            self.ua[m[1]] = f"client-{m[1]}"
            return {}
        m = re.fullmatch(r"/api/v1/projects/proj-1/identity-memberships/([^/]+)", route)
        if m and method == "POST":
            name = next(n for n, i in self.ids.items() if i == m[1])
            self.members[name] = [body["role"]]
            return {}
        m = re.fullmatch(UA + r"/identities/([^/]+)/client-secrets", route)
        if m and method == "POST":
            csid = self._uuid()
            value = f"SECRETVALUE-{len(self.minted_values)}-xYz9"
            self.minted_values.append(value)
            self.secrets[csid] = {"description": body["description"], "revoked": False,
                                  "ttl": body["ttl"], "uses": body["numUsesLimit"]}
            return {"clientSecret": value, "clientSecretData": {"id": csid}}
        m = re.fullmatch(UA + r"/identities/([^/]+)/client-secrets/([^/]+)/revoke", route)
        if m and method == "POST":
            if self.fail_revoke:
                raise ApiError(f"POST {route} -> HTTP 500: boom")
            s = self.secrets.get(m[2])
            if s is None:
                raise ApiError(f"POST {route} -> HTTP 404: not found")
            if s["revoked"]:
                raise ApiError(f"POST {route} -> HTTP 400: client secret already revoked")
            s["revoked"] = True
            return {}
        raise AssertionError(f"unexpected {method} {route}")


class FakeGh:
    """gh(args, stdin) -> (rc, out, err), holding the deploy keys of one repo."""

    def __init__(self, fail_hosts=(), fail_delete=False):
        self.calls, self.keys, self._id = [], {}, 4000
        self.fail_titles = {f"org-node:{h}" for h in fail_hosts}
        self.fail_delete = fail_delete

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

def _join(host="node-a", deploy=DEPLOY):
    token = hq_join.mint(host)["token"]
    return hq_join.accept(token, host, "linux", "/opt/MoonieXHQ", PUB, deploy_pubkey=deploy)


def _prov(host="node-a", org=None, gh=None, **kw):
    kw.setdefault("sealer", fake_seal)
    return hq_join.provision(host, org=org, gh=gh, **kw)


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


# --------------------------------------------------- infisical_setup, fake org

def test_infisical_setup_stays_stdlib_only():
    """A Run Inbox card copies this one file: no import outside the standard library."""
    tree = ast.parse(Path(infisical_setup.__file__).read_text(encoding="utf-8"))
    mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module.split(".")[0] for n in ast.walk(tree)
             if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
    assert mods <= set(sys.stdlib_module_names), mods - set(sys.stdlib_module_names)


def test_ensure_node_identity_creates_org_node_as_the_fifth_identity():
    org = FakeOrg()
    iid = infisical_setup.ensure_node_identity(org)
    assert iid == "id-org-node" and len(org.ids) == 5
    assert org.ua[iid] and org.members["org-node"] == ["viewer"]
    posts = [c for c in org.calls if c[0] == "POST"]
    assert posts[0][2]["role"] == "no-access"                     # no org role
    before = len(org.calls)
    assert infisical_setup.ensure_node_identity(org) == iid        # second call creates nothing
    assert [c for c in org.calls[before:] if c[0] == "POST"] == []


def test_a_sixth_identity_is_refused_and_the_names_are_listed():
    org = FakeOrg(idents=("mac", "contabo", "winbox", "setup", "extra"))
    with pytest.raises(infisical_setup.IdentityCapError) as ei:
        infisical_setup.ensure_node_identity(org)
    msg = str(ei.value)
    assert all(n in msg for n in ("mac", "contabo", "winbox", "setup", "extra")) and "5" in msg
    assert [c for c in org.calls if c[0] == "POST"] == []        # nothing was created
    assert "org-node" not in org.ids


def test_org_node_already_there_is_found_even_when_the_org_is_full():
    org = FakeOrg(idents=("mac", "contabo", "winbox", "setup", "org-node"))
    assert infisical_setup.ensure_node_identity(org) == "id-org-node"
    assert len(org.ids) == 5


def test_ensure_repairs_a_half_made_org_node():
    org = FakeOrg(idents=("mac", "contabo", "winbox", "org-node"))
    del org.ua["id-org-node"]                # identity exists, Universal Auth does not
    org.members.pop("org-node")              # and no membership
    infisical_setup.ensure_node_identity(org)
    assert "id-org-node" in org.ua and org.members["org-node"] == ["viewer"]


def test_ensure_refuses_an_org_node_that_is_wider_than_viewer():
    org = FakeOrg(idents=("mac", "org-node"))
    org.members["org-node"] = ["admin"]
    with pytest.raises(ApiError, match="viewer"):
        infisical_setup.ensure_node_identity(org)


def test_mint_returns_the_value_once_prints_nothing_and_sets_no_ttl(capsys):
    org = FakeOrg()
    out = infisical_setup.mint_node_secret(org, "node-a")
    assert set(out) == {"client_id", "client_secret", "client_secret_id"}
    assert out["client_secret"] == org.minted_values[0] and out["client_id"] == "client-id-org-node"
    assert org.secrets[out["client_secret_id"]] == {
        "description": "org-node:node-a", "revoked": False, "ttl": 0, "uses": 0}
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err == ""
    assert out["client_secret"] not in json.dumps(org.calls)      # it was a response, never a request


def test_mint_refuses_a_second_live_secret_for_the_same_host():
    org = FakeOrg()
    first = infisical_setup.mint_node_secret(org, "node-a")
    with pytest.raises(ApiError, match="already") as ei:
        infisical_setup.mint_node_secret(org, "node-a")
    assert first["client_secret_id"] in str(ei.value) and first["client_secret"] not in str(ei.value)
    infisical_setup.revoke_node_secret(org, first["client_secret_id"])
    assert infisical_setup.mint_node_secret(org, "node-a")["client_secret_id"] != first["client_secret_id"]
    assert infisical_setup.mint_node_secret(org, "node-b")                    # other hosts unaffected


@pytest.mark.parametrize("host", ["", "A", "node a", "../x", "node-", "x" * 40, None])
def test_mint_refuses_a_bad_host_name_before_any_call(host):
    org = FakeOrg()
    with pytest.raises(ApiError, match="host"):
        infisical_setup.mint_node_secret(org, host)
    assert org.calls == []


def test_a_malformed_create_response_never_echoes_the_value():
    org = FakeOrg()
    real_send = org.send

    def odd(method, route, body=None, **q):
        if route.endswith("/client-secrets") and method == "POST":
            return {"clientSecret": "VALUE-SHOULD-NOT-APPEAR", "clientSecretData": {"id": "not-a-uuid"}}
        return real_send(method, route, body, **q)

    org.send = odd
    with pytest.raises(ApiError) as ei:
        infisical_setup.mint_node_secret(org, "node-a")
    assert "VALUE-SHOULD-NOT-APPEAR" not in str(ei.value)


def test_revoke_is_idempotent_and_targets_one_secret():
    org = FakeOrg()
    a = infisical_setup.mint_node_secret(org, "node-a")["client_secret_id"]
    b = infisical_setup.mint_node_secret(org, "node-b")["client_secret_id"]
    infisical_setup.revoke_node_secret(org, a)
    assert org.secrets[a]["revoked"] and not org.secrets[b]["revoked"]
    infisical_setup.revoke_node_secret(org, a)                         # already revoked: 400 -> done
    infisical_setup.revoke_node_secret(org, "00000000-0000-4000-8000-00000000ffff")   # 404 -> done
    assert len(org.live()) == 1


def test_revoke_with_no_org_node_identity_is_done_and_a_real_error_raises():
    infisical_setup.revoke_node_secret(FakeOrg(), "00000000-0000-4000-8000-000000000001")
    org = FakeOrg()
    sid = infisical_setup.mint_node_secret(org, "node-a")["client_secret_id"]
    org.fail_revoke = True
    with pytest.raises(ApiError, match="HTTP 500"):
        infisical_setup.revoke_node_secret(org, sid)


@pytest.mark.parametrize("bad", ["", "../../x", "abc", "00000000-0000-4000-8000-00000000000g", None])
def test_revoke_refuses_an_id_that_is_not_a_uuid_before_any_call(bad):
    org = FakeOrg()
    with pytest.raises(ApiError):
        infisical_setup.revoke_node_secret(org, bad)
    assert org.calls == []


def test_list_and_the_node_secrets_verb_show_no_value(capsys):
    org = FakeOrg()
    infisical_setup.mint_node_secret(org, "node-a")
    rows = infisical_setup.list_node_secrets(org)
    assert rows == [{"description": "org-node:node-a", "id": next(iter(org.secrets)),
                     "created": "2026-10-01T00:00:00Z", "revoked": False}]
    infisical_setup.cmd_node_secrets(org)
    out = capsys.readouterr().out
    assert "org-node:node-a" in out and org.minted_values[0] not in out
    assert infisical_setup.list_node_secrets(FakeOrg()) == []          # no org-node: nothing, nothing made


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
    capsys.readouterr()
    tok = hq_join.mint("node-b")["token"]
    assert hq_join.main(["accept", "--host", "node-b", "--os", "linux", "--hq-root", "/opt/x",
                         "--pubkey", PUB, "--token", tok]) == 0
    assert db.get_host("node-b")["deploy_pubkey"] is None


def test_a_rejoin_replaces_the_deploy_key():
    _join()
    db.upsert_host("node-a", status="left")
    other = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA" + "C" * 43
    _join("node-a", deploy=other)
    assert db.get_host("node-a")["deploy_pubkey"] == other


# ---------------------------------------------------------------- provision

def test_provision_happy_path_seals_stores_and_flips_the_status():
    _join()
    org, gh = FakeOrg(), FakeGh()
    res = _prov(org=org, gh=gh, now=T0)
    assert res["host"] == "node-a" and res["status"] == "identity_ready" and res["changed"] is True
    assert _status() == "identity_ready"
    (sid,) = org.live()
    (kid,) = gh.keys
    row = _ns()
    assert row["infisical_client_secret_id"] == sid and row["github_deploy_key_id"] == str(kid)
    assert row["revoked_at"] is None and row["fetched_at"] is None and row["created_at"]
    recipient, plain = unseal(row["ciphertext"])
    assert recipient == PUB
    assert plain == {"v": 1, "host": "node-a", "client_id": "client-id-org-node",
                     "client_secret": org.minted_values[0]}
    assert gh.keys[kid] == {"title": "org-node:node-a", "key": DEPLOY, "read_only": True}
    assert org.secrets[sid]["description"] == "org-node:node-a"
    assert len(org.ids) == 5 and "org-node" in org.ids
    assert _events("node_provisioned")


def test_provision_without_a_deploy_key_makes_none():
    _join(deploy=None)
    org, gh = FakeOrg(), FakeGh()
    _prov(org=org, gh=gh)
    assert gh.calls == [] and _ns()["github_deploy_key_id"] is None
    assert _status() == "identity_ready" and _ns()["ciphertext"]


def test_the_secret_value_is_nowhere_but_inside_the_ciphertext(capsys, caplog):
    caplog.set_level(logging.DEBUG)
    _join()
    org, gh = FakeOrg(), FakeGh()
    _prov(org=org, gh=gh)
    value = org.minted_values[0]
    assert unseal(_ns()["ciphertext"])[1]["client_secret"] == value       # it did go into the blob...
    assert value not in _all_text()                                       # ...and not into any column
    cap = capsys.readouterr()
    assert value not in cap.out + cap.err and value not in caplog.text
    assert value not in json.dumps(gh.calls) and value not in json.dumps(org.calls)


def test_the_secret_value_is_absent_from_a_failure_too(capsys, caplog):
    caplog.set_level(logging.DEBUG)
    _join()
    org, gh = FakeOrg(), FakeGh(fail_hosts=["node-a"])
    err = _refusal(_prov, org=org, gh=gh)
    value = org.minted_values[0]
    assert value not in err.message and value not in repr(err) and value not in _all_text()
    cap = capsys.readouterr()
    assert value not in cap.out + cap.err and value not in caplog.text


def test_an_error_that_carries_the_value_is_scrubbed():
    _join()
    org, gh = FakeOrg(), FakeGh()

    def leaky(recipient, data):
        raise RuntimeError("sealer said: " + json.loads(data)["client_secret"])

    err = _refusal(_prov, org=org, gh=gh, sealer=leaky)
    assert org.minted_values[0] not in err.message and org.live() == []


def test_provision_cli_value_never_reaches_stdout_or_stderr(monkeypatch, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    _join()
    org, gh = FakeOrg(), FakeGh()
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setattr(hq_join, "is_admin_host", lambda: True)
    monkeypatch.setattr(infisical_setup, "Org", lambda *a, **k: org)
    monkeypatch.setattr(hq_join, "_gh_subprocess", gh)
    monkeypatch.setattr(sealed, "seal", fake_seal)
    assert hq_join.main(["provision", "--host", "node-a"]) == 0
    cap = capsys.readouterr()
    out = json.loads(cap.out)
    assert out["ok"] is True and out["host"] == "node-a" and out["status"] == "identity_ready"
    assert org.minted_values[0] not in cap.out + cap.err + caplog.text + _all_text()


def test_a_sixth_identity_leaves_the_row_pending_and_mints_nothing():
    _join()
    org = FakeOrg(idents=("mac", "contabo", "winbox", "setup", "extra"))
    err = _refusal(_prov, org=org, gh=FakeGh())
    assert err.code == "provision_failed"
    assert org.secrets == {} and "org-node" not in org.ids
    assert _status() == "pending_identity" and _ns() is None             # the claim was dropped


def test_mint_then_gh_fails_revokes_the_mint():
    _join()
    org, gh = FakeOrg(), FakeGh(fail_hosts=["node-a"])
    err = _refusal(_prov, org=org, gh=gh)
    assert err.code == "provision_failed"
    assert len(org.secrets) == 1 and org.live() == []                     # minted, then revoked
    assert gh.keys == {} and _status() == "pending_identity" and _ns() is None
    assert _events("node_provision_failed")


def test_a_sealer_failure_after_the_mint_revokes_it_and_makes_no_deploy_key():
    _join()
    org, gh = FakeOrg(), FakeGh()

    def no_age(recipient, data):
        raise sealed.SealError("age is not installed")

    err = _refusal(_prov, org=org, gh=gh, sealer=no_age)
    assert err.code == "provision_failed" and org.live() == [] and gh.calls == []
    assert _status() == "pending_identity" and _ns() is None


def test_a_hub_failure_right_after_the_mint_still_revokes_the_secret(monkeypatch):
    _join()
    org, gh = FakeOrg(), FakeGh()
    real = hq_join._exec

    def hub_drops_the_id_write(sql, params=()):
        if "SET infisical_client_secret_id" in sql:
            raise RuntimeError("hub went away")
        return real(sql, params)

    monkeypatch.setattr(hq_join, "_exec", hub_drops_the_id_write)
    err = _refusal(_prov, org=org, gh=gh)
    assert err.code == "provision_failed" and org.live() == []            # revoked by the id in memory


def test_when_the_revoke_also_fails_the_orphans_are_named_and_kept():
    _join()
    org, gh = FakeOrg(fail_revoke=True), FakeGh(fail_hosts=["node-a"])
    err = _refusal(_prov, org=org, gh=gh, now=T0)
    (sid,) = org.secrets
    assert err.code == "provision_orphans" and sid in err.message
    row = _ns()
    assert row["infisical_client_secret_id"] == sid and row["ciphertext"] is None
    assert row["revoked_at"] is None and _status() == "pending_identity"


def test_a_run_in_progress_blocks_a_second_one_and_a_stale_one_is_cleaned_up():
    _join()
    org, gh = FakeOrg(fail_revoke=True), FakeGh(fail_hosts=["node-a"])
    _refusal(_prov, org=org, gh=gh, now=T0)
    (old,) = org.secrets
    minted = len(org.minted_values)

    org.fail_revoke = False
    gh.fail_titles.clear()
    err = _refusal(_prov, org=org, gh=gh, now=T0 + timedelta(minutes=1))
    assert err.code == "busy" and len(org.minted_values) == minted        # nothing new was minted

    res = _prov(org=org, gh=gh, now=T0 + timedelta(minutes=11))
    assert res["changed"] is True and _status() == "identity_ready"
    assert org.secrets[old]["revoked"] is True                            # the leftover was revoked
    assert org.live() == [_ns()["infisical_client_secret_id"]] and len(org.live()) == 1


def test_provision_twice_is_a_no_op():
    _join()
    org, gh = FakeOrg(), FakeGh()
    first = _prov(org=org, gh=gh, now=T0)
    snap = (len(org.calls), len(gh.calls), _ns(), len(org.minted_values))
    again = _prov(org=org, gh=gh, now=T0 + timedelta(hours=2))
    assert again["changed"] is False and again["status"] == "identity_ready"
    assert (len(org.calls), len(gh.calls), _ns(), len(org.minted_values)) == snap
    assert first["changed"] is True and len(_events("node_provisioned")) == 1


def test_provision_refuses_the_wrong_kind_of_row():
    assert _refusal(_prov, "ghost-node", org=FakeOrg(), gh=FakeGh()).code == "unknown_host"
    db.seed_hosts_from_config()
    assert _refusal(_prov, "mac", org=FakeOrg(), gh=FakeGh()).code == "not_joined"
    _join()
    for status in ("online", "left"):
        db.upsert_host("node-a", status=status)
        err = _refusal(_prov, org=FakeOrg(), gh=FakeGh())
        assert err.code == "bad_status" and status in err.message


def test_a_rejoined_node_is_provisioned_afresh():
    _join()
    org, gh = FakeOrg(), FakeGh()
    _prov(org=org, gh=gh)
    hq_join.leave("node-a", live=True, revokers=_all_ok(org, gh))
    assert _status() == "left" and _ns()["revoked_at"]
    _join()                                                               # same name, new token
    res = _prov(org=org, gh=gh, now=T0 + timedelta(hours=1))
    assert res["changed"] is True and _status() == "identity_ready"
    row = _ns()
    assert row["revoked_at"] is None and row["ciphertext"] and len(org.live()) == 1


# --------------------------------------------------------------------- sealed

def test_sealed_prints_the_stored_ciphertext_and_stamps_fetched_at_once(capsys):
    _join()
    _prov(org=FakeOrg(), gh=FakeGh())
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
    org, gh = FakeOrg(), FakeGh()
    _prov(org=org, gh=gh)
    hq_join.leave("node-a", live=True, revokers=_all_ok(org, gh))
    assert _refusal(hq_join.sealed_ciphertext, "node-a").code == "not_provisioned"   # revoked


# ---------------------------------------------------- the CLI and the live gate

def test_provision_cli_is_refused_without_the_flag_and_builds_no_org(monkeypatch, capsys):
    _join()
    monkeypatch.setattr(infisical_setup, "Org", lambda *a, **k: pytest.fail("logged in"))
    assert hq_join.main(["provision", "--host", "node-a"]) == 2
    assert "not_enabled" in capsys.readouterr().err and _status() == "pending_identity"


def test_provision_cli_is_refused_with_the_flag_on_a_host_that_is_not_the_admin(monkeypatch, capsys):
    _join()
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setattr(infisical_setup, "Org", lambda *a, **k: pytest.fail("logged in"))
    assert hq_join.main(["provision", "--host", "node-a"]) == 2
    assert "not_admin_host" in capsys.readouterr().err and _status() == "pending_identity"


@pytest.mark.parametrize("value", ["", "0", "true", "yes", "on", " 1"])
def test_only_the_exact_string_1_turns_the_flag_on(monkeypatch, value):
    monkeypatch.setenv(hq_join.W42_FLAG, value)
    assert hq_join.w42_enabled() is False
    assert hq_join.default_revokers() is hq_join.UNWIRED_REVOKERS
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    assert hq_join.w42_enabled() is True


def test_admin_host_means_the_setup_file_exists_and_it_is_never_read(monkeypatch, tmp_path):
    creds = tmp_path / "creds"
    monkeypatch.setattr(infisical_setup, "CRED_DIR", str(creds))
    assert hq_join.is_admin_host() is False
    creds.mkdir()
    f = creds / f"{infisical_setup.SETUP}.env"
    f.write_text("INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET=not-read\n")
    f.chmod(0)                                                            # unreadable: exists() still works
    try:
        assert hq_join.is_admin_host() is True
    finally:
        f.chmod(stat.S_IRUSR | stat.S_IWUSR)


# ------------------------------------------------------------- leave, wired

def _all_ok(org, gh):
    """The wired legs plus stand-ins for the two that stay unwired in W4.2."""
    ok = lambda step: hq_join.Outcome(True, "")          # noqa: E731
    return {**hq_join.wired_revokers(org=org, gh=gh), "tailscale_device": ok, "authorized_keys": ok}


def test_leave_live_with_wired_revokers_revokes_the_stored_ids_and_ends_left():
    db.seed_hosts_from_config()
    _join("node-a")
    _join("node-b")
    org, gh = FakeOrg(), FakeGh()
    _prov("node-a", org=org, gh=gh)
    _prov("node-b", org=org, gh=gh)
    a, b = _ns("node-a"), _ns("node-b")
    assert a["infisical_client_secret_id"] != b["infisical_client_secret_id"]

    res = hq_join.leave("node-a", live=True, revokers=_all_ok(org, gh))
    assert res["status"] == "left" and res["left_behind"] == [] and _status("node-a") == "left"
    # exactly this host's two things, by the ids that were stored:
    assert org.revoke_routes() == [f"{UA}/identities/id-org-node/client-secrets/"
                                   f"{a['infisical_client_secret_id']}/revoke"]
    assert [c[0] for c in gh.calls if "DELETE" in c[0]] == [
        ["api", f"repos/{hq_join.GH_REPO}/keys/{a['github_deploy_key_id']}", "-X", "DELETE"]]
    assert org.live() == [b["infisical_client_secret_id"]] and list(gh.keys) == [int(b["github_deploy_key_id"])]
    row = _ns("node-a")
    assert row["revoked_at"] and row["ciphertext"] is None and row["github_deploy_key_id"] is None
    assert row["infisical_client_secret_id"] == a["infisical_client_secret_id"]    # audit trail kept
    assert _ns("node-b")["ciphertext"] and _status("node-b") == "identity_ready"    # untouched
    hq_join.leave("node-a", live=True, revokers=_all_ok(org, gh))
    assert len(org.revoke_routes()) == 1                                            # idempotent


def test_leave_with_the_default_table_and_the_flag_revokes_two_legs_and_stays_partial(monkeypatch):
    db.seed_hosts_from_config()
    _join()
    org, gh = FakeOrg(), FakeGh()
    _prov(org=org, gh=gh)
    lives = []
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setattr(hq_join, "_live_org", lambda: lives.append(1) or org)
    monkeypatch.setattr(hq_join, "_gh_subprocess", gh)
    res = hq_join.leave("node-a", live=True)                # no revokers passed: the default table
    by_kind = {}
    for s in res["steps"]:
        by_kind.setdefault(s["kind"], []).append(s)
    assert by_kind["infisical_client_secret"][0]["ok"] and by_kind["github_deploy_key"][0]["ok"]
    assert not by_kind["tailscale_device"][0]["ok"] and "not wired yet" in by_kind["tailscale_device"][0]["detail"]
    assert all(not s["ok"] for s in by_kind["authorized_keys"])
    assert res["status"] == "partial" and _status() == "identity_ready"
    assert org.live() == [] and gh.keys == {}
    res = hq_join.leave("node-a", live=True)                # converges: revoke again is fine
    assert res["status"] == "partial" and _ns()["revoked_at"]


def test_leave_without_the_flag_still_refuses_every_step():
    db.seed_hosts_from_config()
    _join()
    _prov(org=FakeOrg(), gh=FakeGh())
    res = hq_join.leave("node-a", live=True)
    assert res["status"] == "partial" and all(not s["ok"] for s in res["steps"])
    assert _ns()["revoked_at"] is None


def test_a_failing_revoke_leaves_the_row_and_the_ids_for_the_next_run():
    db.seed_hosts_from_config()
    _join()
    org, gh = FakeOrg(), FakeGh(fail_delete=True)
    _prov(org=org, gh=gh)
    table = _all_ok(org, gh)
    res = hq_join.leave("node-a", live=True, revokers=table)
    assert res["status"] == "partial" and any(k.startswith("github_deploy_key") for k in res["left_behind"])
    assert _ns()["revoked_at"] and _ns()["github_deploy_key_id"]          # key id kept: not deleted
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


def _live_env(monkeypatch, org, gh, admin=True):
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setattr(hq_join, "is_admin_host", lambda: admin)
    monkeypatch.setattr(infisical_setup, "Org", lambda *a, **k: org)
    monkeypatch.setattr(hq_join, "_gh_subprocess", gh)
    monkeypatch.setattr(sealed, "seal", fake_seal)


def test_the_watchdog_pass_is_a_no_op_without_the_flag(monkeypatch):
    _pending("node-a")
    monkeypatch.setattr(hq_join, "is_admin_host", lambda: True)
    monkeypatch.setattr(infisical_setup, "Org", lambda *a, **k: pytest.fail("logged in"))
    monkeypatch.setattr(watchdog, "_provision_retry_at", {})
    assert watchdog._provision_identities() == []
    assert _status("node-a") == "pending_identity" and _ns("node-a") is None


def test_the_watchdog_pass_is_a_no_op_on_a_host_that_is_not_the_admin(monkeypatch):
    _pending("node-a")
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setattr(infisical_setup, "Org", lambda *a, **k: pytest.fail("logged in"))
    monkeypatch.setattr(watchdog, "_provision_retry_at", {})
    assert hq_join.is_admin_host() is False                 # CRED_DIR points at nothing
    assert watchdog._provision_identities() == []
    assert _status("node-a") == "pending_identity"


def test_the_watchdog_pass_provisions_every_pending_row_and_one_bad_row_stops_nobody(monkeypatch):
    _pending("node-a", "node-b", "node-c")
    db.upsert_host("node-d", os="linux", status="online")  # not pending: left alone
    org, gh = FakeOrg(), FakeGh(fail_hosts=["node-b"])
    _live_env(monkeypatch, org, gh)
    monkeypatch.setattr(watchdog, "_provision_retry_at", {})
    results = watchdog._provision_identities()
    by_host = {r["host"]: r for r in results}
    assert set(by_host) == {"node-a", "node-b", "node-c"}
    assert by_host["node-a"]["changed"] and by_host["node-c"]["changed"]
    assert "error" in by_host["node-b"]
    assert [_status(h) for h in ("node-a", "node-b", "node-c")] == [
        "identity_ready", "pending_identity", "identity_ready"]
    assert len(org.live()) == 2 and len(gh.keys) == 2


def test_a_failed_host_is_left_alone_for_an_hour_then_retried(monkeypatch):
    _pending("node-b")
    org, gh = FakeOrg(), FakeGh(fail_hosts=["node-b"])
    _live_env(monkeypatch, org, gh)
    monkeypatch.setattr(watchdog, "_provision_retry_at", {})
    assert "error" in watchdog._provision_identities()[0]
    minted = len(org.minted_values)
    assert watchdog._provision_identities() == []           # backing off: no second mint
    assert len(org.minted_values) == minted
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
