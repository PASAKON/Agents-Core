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
    cap = capsys.readouterr()
    assert secret not in cap.out + cap.err
    assert "postgresql://org:***@h:5432/org_test" in cap.err
    # stdout stays clean: the org MCP server speaks JSON-RPC on it (2026-10-03, mesh_check
    # logged "Failed to parse JSONRPC message" on this banner)
    assert cap.out == ""


def test_pg_dump_never_gets_the_password_on_its_command_line(tmp_path, monkeypatch):
    """The nightly hub backup (tools/drive_leg.py state-db) used to run
    `pg_dump <ORG_DB_URL>`: the password sat in argv, which `ps` shows to every
    user on Contabo, and the failure message printed argv into the cron log."""
    import os

    import pytest

    import tools.drive_leg as drive_leg

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "pg_dump"
    stub.write_text(
        "#!/bin/sh\n"
        f'echo "$@" > {tmp_path / "argv"}\n'
        f'printf %s "$PGPASSWORD" > {tmp_path / "pw"}\n'
        "echo 'connection refused' >&2\n"
        "exit 1\n"
    )
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("ORG_DB_URL", "postgresql://org:s3cr3t%40Pass@h:5432/org?sslmode=disable")
    cfg = tmp_path / "cfg"
    (cfg / "logs").mkdir(parents=True)

    with pytest.raises(drive_leg.DriveLegError) as err:
        drive_leg.state_db(config_dir=cfg)

    argv = (tmp_path / "argv").read_text()
    assert "s3cr3t" not in argv
    assert "s3cr3t" not in str(err.value)
    assert "postgresql://org@h:5432/org?sslmode=disable" in argv
    assert (tmp_path / "pw").read_text() == "s3cr3t@Pass"
