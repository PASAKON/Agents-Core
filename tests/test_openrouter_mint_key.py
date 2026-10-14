"""tools/openrouter_mint_key.py: one capped key, filed in Infisical, never printed; a failed put leaves no key."""
from __future__ import annotations

import io
import subprocess

import pytest

from tools import openrouter_mint_key as m

ADMIN = "test-admin-value-not-a-key-0000"
NEW = "test-new-value-not-a-key-9z7Q"
ARGS = ["--name", "mooniex-sompong-prod-jev-exp2027-01-14", "--limit", "1", "--reset", "monthly",
        "--to", "MoonieX-SomPong/prod/OPENROUTER_API_KEY_JEV", "--comment", "Jev filter",
        "--meta", "owner=cto"]


class FakeOR:
    def __init__(self, names=(), create_status=200, delete_status=200):
        self.names = list(names)
        self.create_status = create_status
        self.delete_status = delete_status
        self.calls: list[tuple[str, str, dict, object]] = []

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        if method == "GET":
            return 200, {"data": [{"name": n, "hash": f"h{i}"} for i, n in enumerate(self.names)]}
        if method == "POST":
            return self.create_status, {"key": NEW, "data": {"hash": "abcdef0123456789", "name": body["name"]}}
        if method == "DELETE":
            return self.delete_status, None
        raise AssertionError(method)


class FakeRun:
    def __init__(self, put_rc=0, last4=NEW[-4:]):
        self.put_rc = put_rc
        self.last4 = last4
        self.calls: list[tuple[list, dict]] = []

    def __call__(self, argv, **kw):
        self.calls.append((argv, kw))
        verb = argv[2]
        if verb == "put":
            return subprocess.CompletedProcess(argv, self.put_rc, "", "403 forbidden" if self.put_rc else "")
        if verb == "last4":
            return subprocess.CompletedProcess(
                argv, 0, f"MoonieX-SomPong/prod OPENROUTER_API_KEY_JEV · last4={self.last4}\n", "")
        raise AssertionError(verb)


@pytest.fixture(autouse=True)
def _admin(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY_ADMIN", ADMIN)


def _go(http, run):
    out = io.StringIO()
    rc = m.mint(m.parse(ARGS), http=http, run=run, out=out)
    return rc, out.getvalue()


def test_happy_path_creates_capped_key_and_files_it_without_printing_it():
    http, run = FakeOR(), FakeRun()
    rc, out = _go(http, run)
    assert rc == 0
    post = [c for c in http.calls if c[0] == "POST"]
    assert post[0][3] == {"name": "mooniex-sompong-prod-jev-exp2027-01-14", "limit": 1.0, "limit_reset": "monthly"}
    put_argv, put_kw = run.calls[0]
    assert put_argv[2:6] == ["put", "MoonieX-SomPong", "prod", "OPENROUTER_API_KEY_JEV"]
    assert put_argv[put_argv.index("--as") + 1] == "setup"
    assert put_kw["input"] == NEW + "\n"                       # value only on stdin
    assert NEW not in " ".join(put_argv)                        # never in argv
    assert not any(k.startswith("OPENROUTER_") for k in put_kw["env"])  # no provider key in the child
    assert "last4 match: yes" in out
    assert NEW not in out and NEW[-8:] not in out and ADMIN not in out


def test_existing_name_refuses_before_creating():
    http = FakeOR(names=["mooniex-sompong-prod-jev-exp2027-01-14"])
    with pytest.raises(m.MintError, match="already exists"):
        _go(http, FakeRun())
    assert not [c for c in http.calls if c[0] == "POST"]


def test_failed_put_deletes_the_new_key():
    http, run = FakeOR(), FakeRun(put_rc=1)
    with pytest.raises(m.MintError, match="infisical put exit 1"):
        _go(http, run)
    deletes = [c for c in http.calls if c[0] == "DELETE"]
    assert len(deletes) == 1 and deletes[0][1].endswith("/keys/abcdef0123456789")


def test_failed_put_and_failed_delete_still_refuses_and_names_the_hash(capsys):
    http, run = FakeOR(delete_status=500), FakeRun(put_rc=1)
    out = io.StringIO()
    with pytest.raises(m.MintError):
        m.mint(m.parse(ARGS), http=http, run=run, out=out)
    assert "delete failed" in out.getvalue() and "abcdef01" in out.getvalue()
    assert NEW not in out.getvalue()


def test_last4_mismatch_returns_nonzero():
    rc, out = _go(FakeOR(), FakeRun(last4="XXXX"))
    assert rc == 3 and "last4 match: NO" in out


def test_create_error_raises_and_puts_nothing():
    run = FakeRun()
    with pytest.raises(m.MintError, match="create key HTTP 402"):
        _go(FakeOR(create_status=402), run)
    assert run.calls == []


def test_no_admin_key_refuses(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY_ADMIN")
    with pytest.raises(m.MintError, match="OPENROUTER_API_KEY_ADMIN"):
        _go(FakeOR(), FakeRun())


@pytest.mark.parametrize("bad", [
    ["--limit", "0"], ["--limit", "50"], ["--name", "Has Spaces"], ["--name", "x" * 41], ["--reset", "yearly"],
])
def test_bad_arguments_are_refused(bad):
    argv = list(ARGS)
    i = argv.index(bad[0])
    argv[i + 1] = bad[1]
    with pytest.raises(SystemExit):
        m.parse(argv)


def test_bad_target_refused():
    argv = list(ARGS)
    argv[argv.index("--to") + 1] = "MoonieX-SomPong/staging/X"
    with pytest.raises(m.MintError, match="--to"):
        m.mint(m.parse(argv), http=FakeOR(), run=FakeRun(), out=io.StringIO())
