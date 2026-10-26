"""Tests for scripts/resolve-resume-id.sh (Part B.3).

Verifies UUID pass-through, lockfile resolution, hub fallback resolution, surfacing of the last
hub stderr line prefixed with 'hub: ' on failure, and stripping of postgres/postgresql DSNs.
"""
from __future__ import annotations

import os
import subprocess
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "resolve-resume-id.sh"
SAMPLE_UUID = "d405e3e2-1111-2222-3333-a6f2f69c4825"


@pytest.mark.parametrize('message,category', [
    ('OperationalError: host=db user=x password=FAKE dbname=y', 'unreachable or refused (OperationalError)'),
    ('Failure: postgresql://x:FAKE@db/y password=FAKE', 'error'),
])
def test_backend_text_never_leaks(tmp_path, message, category):
    fake = tmp_path / 'hub'
    fake.write_text(f"#!/bin/sh\necho '{message}' >&2\nexit 1\n")
    fake.chmod(0o755)
    result = _run_resolve('cto', '1234abcd', locks_dir=tmp_path, org_python=fake)
    assert result.returncode == 2
    assert f'hub: {category}' in result.stderr
    assert 'FAKE' not in result.stderr and 'password' not in result.stderr


def _run_resolve(role: str, value: str, *, locks_dir: Path, org_python: Path | None = None,
                 extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["RESOLVE_LOCKS_DIR"] = str(locks_dir)
    if org_python is not None:
        env["RESOLVE_ORG_PYTHON"] = str(org_python)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT), role, value],
        capture_output=True, text=True, env=env, cwd=str(ROOT),
    )


def test_full_uuid_passes_through_directly(tmp_path):
    r = _run_resolve("cto", SAMPLE_UUID, locks_dir=tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == SAMPLE_UUID


def test_invalid_session_id_is_refused(tmp_path):
    r = _run_resolve("cto", "not-hex!", locks_dir=tmp_path)
    assert r.returncode == 2
    assert "expected 8 lowercase hex characters or a full UUID" in r.stderr


def test_resolves_from_uuid_lock_file_without_hub(tmp_path):
    (tmp_path / "cto-f69c4825.uuid").write_text(SAMPLE_UUID + "\n")
    fake_py = tmp_path / "fail_py.sh"
    fake_py.write_text("#!/usr/bin/env bash\nexit 99\n")
    fake_py.chmod(0o755)
    r = _run_resolve("cto", "f69c4825", locks_dir=tmp_path, org_python=fake_py)
    assert r.returncode == 0
    assert r.stdout.strip() == SAMPLE_UUID


def test_resolves_from_hub_when_lock_file_missing(tmp_path):
    fake_py = tmp_path / "ok_py.sh"
    fake_py.write_text(f"#!/usr/bin/env bash\necho '{SAMPLE_UUID}'\n")
    fake_py.chmod(0o755)
    r = _run_resolve("cto", "f69c4825", locks_dir=tmp_path, org_python=fake_py)
    assert r.returncode == 0
    assert r.stdout.strip() == SAMPLE_UUID


def test_hub_failure_surfaces_last_stderr_line_and_strips_postgres_dsn(tmp_path):
    fake_py = tmp_path / "err_py.sh"
    fake_py.write_text(
        "#!/usr/bin/env bash\n"
        "echo 'Traceback (most recent call last):' >&2\n"
        "echo 'HubConnectError: failed connecting to postgresql://org_coo:SuperSecretPass123@100.64.0.1:5432/org_hub (timeout)' >&2\n"
        "exit 1\n"
    )
    fake_py.chmod(0o755)
    r = _run_resolve("cto", "f69c4825", locks_dir=tmp_path, org_python=fake_py)
    assert r.returncode == 2
    assert "refuse to resume cto-f69c4825" in r.stderr
    assert "hub: unreachable or refused (HubConnectError)" in r.stderr
    assert "SuperSecretPass123" not in r.stderr
    assert "postgresql://" not in r.stderr
    assert "postgres://" not in r.stderr


def test_hub_failure_strips_postgres_scheme_variants(tmp_path):
    fake_py = tmp_path / "err_pg.sh"
    fake_py.write_text(
        "#!/usr/bin/env bash\n"
        "echo 'OperationalError: dsn postgres://admin:Hunter2Secret@db.internal:5432/main refused' >&2\n"
        "exit 1\n"
    )
    fake_py.chmod(0o755)
    r = _run_resolve("cmo", "1234abcd", locks_dir=tmp_path, org_python=fake_py)
    assert r.returncode == 2
    assert "hub: unreachable or refused (OperationalError)" in r.stderr
    assert "Hunter2Secret" not in r.stderr
    assert "postgres://" not in r.stderr
