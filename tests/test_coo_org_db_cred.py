"""The COO session's hub DSN: scripts/coo-org-db-cred.sh writes it, with-org-db-env.sh reads it.

CEO 2026-10-02: SomPong (unix user `sompong`) gets the org MCP with a key that opens only the limited
Postgres role org_coo. Infisical Free has no identity slot left, so mooniex-sompong.service (root,
identity `contabo`) reads Infisical Org-Coo at start and leaves the DSN as one root:sompong 0440 file
in /run/sompong-coo; the org MCP's wrapper reads it into its own environment (leg a2). Every test here
uses a tmp dir and a fake DSN; nothing reaches Infisical or Postgres.

Run: .venv/bin/python -m pytest tests/test_coo_org_db_cred.py
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WRITER = ROOT / "scripts" / "coo-org-db-cred.sh"
WRAPPER = ROOT / "scripts" / "hub" / "with-org-db-env.sh"
UNIT = ROOT / "deploy" / "systemd" / "mooniex-sompong.service"
DSN = "postgresql://org_coo:not-a-real-password@127.0.0.1:5432/org"


def write(tmp_path: Path, **env) -> subprocess.CompletedProcess:
    base = {"PATH": "/usr/bin:/bin", "COO_CRED_DIR": str(tmp_path), "COO_CRED_CHOWN": "0"}
    return subprocess.run(["bash", str(WRITER)], env={**base, **env}, capture_output=True, text=True)


def test_writer_leaves_the_dsn_in_one_0440_file_and_never_prints_it(tmp_path):
    r = write(tmp_path, ORG_DB_URL=DSN)
    assert r.returncode == 0, r.stderr
    out = tmp_path / "org-db.url"
    assert out.read_text() == DSN
    assert stat.S_IMODE(out.stat().st_mode) == 0o440
    assert "not-a-real-password" not in r.stdout + r.stderr
    assert [p.name for p in tmp_path.iterdir()] == ["org-db.url"]  # no temp file left behind


@pytest.mark.parametrize("value", ["", "mysql://x@y/z", "not a dsn"])
def test_writer_refuses_a_missing_or_foreign_value(tmp_path, value):
    r = write(tmp_path, ORG_DB_URL=value)
    assert r.returncode != 0
    assert not (tmp_path / "org-db.url").exists()


def test_writer_refuses_a_linked_directory(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    r = write(tmp_path, ORG_DB_URL=DSN, COO_CRED_DIR=str(link))
    assert r.returncode != 0
    assert not (real / "org-db.url").exists()


@pytest.mark.skipif(os.geteuid() != 0, reason="checks the root-owned directory rule; needs root")
def test_writer_as_root_refuses_a_directory_root_does_not_own(tmp_path):
    d = tmp_path / "theirs"
    d.mkdir()
    os.chown(d, 65534, 65534)
    r = write(tmp_path, ORG_DB_URL=DSN, COO_CRED_DIR=str(d), COO_CRED_CHOWN="1")
    assert r.returncode != 0 and "must be root's" in r.stderr


def wrap(tmp_path: Path, **env) -> subprocess.CompletedProcess:
    base = {
        "PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home"),
        "MOONIEX_ORG_DB_ENV": str(tmp_path / "no-such.env"),
        "MOONIEX_NODE_YAML": str(tmp_path / "no-such-node.yaml"),
        "INFISICAL_CRED_DIR": str(tmp_path / "no-cred-dir"),
    }
    return subprocess.run(["bash", str(WRAPPER), "printenv", "ORG_DB_URL"], env={**base, **env},
                          capture_output=True, text=True)


def test_wrapper_reads_the_file_into_the_command_environment(tmp_path):
    f = tmp_path / "org-db.url"
    f.write_text(DSN)
    r = wrap(tmp_path, MOONIEX_ORG_DB_URL_FILE=str(f))
    assert r.returncode == 0 and r.stdout.strip() == DSN


def test_wrapper_ignores_a_missing_file(tmp_path):
    r = wrap(tmp_path, MOONIEX_ORG_DB_URL_FILE=str(tmp_path / "gone"))
    assert r.returncode != 0 and r.stdout == ""  # printenv: not set


def test_an_env_file_value_wins_over_the_file(tmp_path):
    env_file = tmp_path / "org-db.env"
    env_file.write_text("ORG_DB_URL=postgresql://from-env-file@h/org\n")
    f = tmp_path / "org-db.url"
    f.write_text(DSN)
    r = wrap(tmp_path, MOONIEX_ORG_DB_ENV=str(env_file), MOONIEX_ORG_DB_URL_FILE=str(f))
    assert r.stdout.strip() == "postgresql://from-env-file@h/org"


def test_unit_writes_the_file_from_org_coo_before_the_supervisor_starts():
    text = UNIT.read_text()
    assert "RuntimeDirectory=sompong-coo" in text
    assert "RuntimeDirectoryMode=0711" in text
    pre = [l for l in text.splitlines() if l.startswith("ExecStartPre=")]
    assert len(pre) == 1
    assert pre[0].startswith("ExecStartPre=-")  # SomPong still starts when Infisical is down
    assert "run Org-Coo prod --as contabo --" in pre[0] and "coo-org-db-cred.sh" in pre[0]
    assert text.index("ExecStartPre=") < text.index("ExecStart=/bin/bash")
