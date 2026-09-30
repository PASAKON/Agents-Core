"""The hub URL is never printed with its password (2026-10-01: the init banner
put it into a session transcript)."""
from lib import db


def test_redact_url_hides_the_password():
    assert db.redact_url("postgresql://org:s3cr3t-Pass_w0rd@100.1.2.3:5432/org_test") == \
        "postgresql://org:***@100.1.2.3:5432/org_test"


def test_redact_url_leaves_urls_without_a_password_alone():
    assert db.redact_url("postgresql://org@host/org") == "postgresql://org@host/org"
    assert db.redact_url("postgresql://host/org") == "postgresql://host/org"
    assert db.redact_url(None) is None
    assert db.redact_url("") == ""


def test_init_banner_does_not_print_the_password(monkeypatch, capsys):
    secret = "s3cr3t-Pass_w0rd"
    monkeypatch.setattr(db, "pg_url", lambda: f"postgresql://org:{secret}@h:5432/org_test")

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(db, "get_conn", lambda: _Conn())
    monkeypatch.setattr(db, "init_schema", lambda conn, is_pg: None)
    db.init()
    out = capsys.readouterr().out
    assert secret not in out
    assert "postgresql://org:***@h:5432/org_test" in out
