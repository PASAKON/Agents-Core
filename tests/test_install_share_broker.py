"""Tests for scripts/install-share-broker.sh and deploy/share-broker/mooniex-share-broker.service
(task-e71026a4: the Drive SHARE broker installed without a credential file).

Nothing here installs anything: every run of the script is `--dry-run` (it prints each step and
changes nothing, no root needed) or the unprivileged `status`. The guards under test:
  - the installer has no code path that writes a credential/.env file or takes a credential argument
  - the unit gets its secret from Infisical (`infisical_setup.py run ... --path /drive-share`) and
    follows the Gmail/COO-gate pattern (no User= with NoNewPrivileges, "+" ExecStartPre install -d)
  - the checkout path that goes through sed into the unit cannot smuggle a substitution
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "install-share-broker.sh"
UNIT = REPO / "deploy" / "share-broker" / "mooniex-share-broker.service"

SENTINEL = "SENTINEL-NEVER-PRINT-THIS-0123456789"


def _bash(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script), *args], capture_output=True, text=True, timeout=60)


def _code_lines(path: Path) -> list[str]:
    """Non-comment, non-blank lines: what actually runs (or configures the unit)."""
    return [ln for ln in path.read_text().splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def test_installer_passes_bash_syntax_check():
    result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_installer_and_unit_have_no_credential_file_code_path():
    """Grep-style guard: nothing that runs in the script or the unit names an env/credential file,
    an OAuth key, or a way to take one from the caller."""
    forbidden = [
        r"\.env\b", r"EnvironmentFile", r"DRIVE_SHARE_BROKER_ENV", r"GOOGLE_OAUTH", r"REFRESH_TOKEN",
        r"CLIENT_SECRET", r"\btee\b", r"drive-share\.env", r"credential-source",
    ]
    for path in (SCRIPT, UNIT):
        for line in _code_lines(path):
            for pattern in forbidden:
                assert not re.search(pattern, line), f"{path.name}: {pattern!r} in code line: {line.strip()}"


def test_installer_redirections_only_ever_target_the_unit_file_devnull_or_stderr():
    allowed = {'"${UNIT_PATH}.new"', "/dev/null", "&1", "&2"}   # &N duplicates a descriptor, writes no file
    seen = set()
    for line in _code_lines(SCRIPT):
        for _fd, target in re.findall(r"(\d?>>?)\s*(&\d|[^\s;|)]+)", line):
            seen.add(target)
            assert target in allowed, f"unexpected redirection target {target!r} in: {line.strip()}"
    assert '"${UNIT_PATH}.new"' in seen   # the guard really parsed the unit write


def test_install_takes_no_credential_file_argument(tmp_path):
    """The retired `install <credential-source-file>` call must now fail, not copy from the file."""
    decoy = tmp_path / "decoy-source"
    decoy.write_text(f"GOOGLE_OAUTH_REFRESH_TOKEN={SENTINEL}\n")
    result = _bash(SCRIPT, "install", str(decoy), "--dry-run")
    assert result.returncode == 2
    assert SENTINEL not in result.stdout + result.stderr
    assert "no credential file" in result.stderr


def test_dry_run_install_renders_the_unit_for_this_checkout_and_changes_nothing():
    touched = [Path("/var/lib/sompong-share"), Path("/var/log/mooniex-share-broker"),
               Path("/etc/systemd/system/mooniex-share-broker.service"),
               Path("/etc/systemd/system/mooniex-share-broker.service.new")]
    before = [p.exists() for p in touched]
    result = _bash(SCRIPT, "install", "--dry-run")
    assert result.returncode == 0, result.stderr
    assert [p.exists() for p in touched] == before

    out = result.stdout
    assert "@ROOT@" not in out
    assert f"WorkingDirectory={REPO}" in out
    assert f"ExecStart=/usr/bin/python3 {REPO}/tools/infisical_setup.py run MoonieX-SomPong prod --as contabo --path /drive-share" in out
    assert "setpriv --reuid=shareup --regid=shareup --clear-groups" in out
    assert "--no-new-privs" in out and "-m runners.drive_share_broker" in out
    assert "ExecStartPre=+/usr/bin/install -d" in out
    assert "install -d -m 0770 -o root -g shareup /var/lib/sompong-share/staging" in out
    assert "chmod 2770 /var/lib/sompong-share/staging" in out
    assert "no file on disk" in out
    # the steps it would take are printed with a "+" prefix, one per command
    plus_lines = [ln for ln in out.splitlines() if ln.startswith("+ ")]
    assert any("systemctl enable mooniex-share-broker" in ln for ln in plus_lines)
    assert any("systemctl restart mooniex-share-broker" in ln for ln in plus_lines)


def test_unit_template_follows_the_gmail_and_coo_gate_pattern():
    lines = _code_lines(UNIT)
    keys = [ln.split("=", 1)[0] for ln in lines if "=" in ln and not ln.startswith("[")]
    # User=/Group= + NoNewPrivileges=true leaves root unable to setresuid: setpriv would fail.
    assert "User" not in keys and "Group" not in keys
    # RuntimeDirectory= is re-chowned to the unit's User= before every command (coo-gate trap).
    assert "RuntimeDirectory" not in keys and "EnvironmentFile" not in keys
    assert "NoNewPrivileges=true" in lines
    assert "RestartPreventExitStatus=2" in lines
    assert "ExecStartPre=+/usr/bin/install -d -m 0750 -o shareup -g shareup /run/mooniex-share-broker" in lines
    assert any(ln.startswith("ReadWritePaths=-/run/mooniex-share-broker ") for ln in lines)
    assert "Environment=DRIVE_SHARE_BROKER_ALLOWED_UIDS=0" in lines
    assert "Environment=DRIVE_SHARE_BROKER_STAGING_ROOT=/var/lib/sompong-share/staging" in lines
    assert "Environment=DRIVE_SHARE_BROKER_SOCKET_PATH=/run/mooniex-share-broker/broker.sock" in lines
    exec_start = next(ln for ln in lines if ln.startswith("ExecStart="))
    assert "run MoonieX-SomPong prod --as contabo --path /drive-share --" in exec_start


def _relocated_tree(base: Path, name: str) -> Path:
    """A minimal copy of what the installer looks at, under a directory called `name`."""
    root = base / name
    (root / "scripts").mkdir(parents=True)
    (root / "deploy" / "share-broker").mkdir(parents=True)
    (root / "runners").mkdir()
    (root / "tools").mkdir()
    shutil.copy(SCRIPT, root / "scripts" / SCRIPT.name)
    shutil.copy(UNIT, root / "deploy" / "share-broker" / UNIT.name)
    (root / "runners" / "drive_share_broker.py").write_text("")
    (root / "tools" / "infisical_setup.py").write_text("")
    return root


def test_relocated_checkout_is_what_gets_rendered(tmp_path):
    root = _relocated_tree(tmp_path, "Core-checkout_2")
    result = _bash(root / "scripts" / SCRIPT.name, "install", "--dry-run")
    assert result.returncode == 0, result.stderr
    assert f"WorkingDirectory={root}" in result.stdout
    assert f"ExecStart=/usr/bin/python3 {root}/tools/infisical_setup.py run" in result.stdout


def test_checkout_path_that_could_break_the_sed_substitution_is_refused(tmp_path):
    for hostile in ("a&b", "a|b", "spaced dir", "paren(thesis)", "hash#dir", "ไทย"):
        root = _relocated_tree(tmp_path, hostile)
        result = _bash(root / "scripts" / SCRIPT.name, "install", "--dry-run")
        assert result.returncode == 2, (hostile, result.stdout, result.stderr)
        assert "unsupported checkout path" in result.stderr
        assert "WorkingDirectory" not in result.stdout


def test_uninstall_dry_run_touches_only_the_unit():
    result = _bash(SCRIPT, "uninstall", "--dry-run")
    assert result.returncode == 0, result.stderr
    steps = [ln for ln in result.stdout.splitlines() if ln.startswith("+ ")]
    assert steps == [
        "+ systemctl disable --now mooniex-share-broker",
        "+ rm -f /etc/systemd/system/mooniex-share-broker.service",
        "+ systemctl daemon-reload",
    ]


def test_status_is_unprivileged_and_reports_no_credential_file():
    result = _bash(SCRIPT, "status")
    assert result.returncode == 0, result.stderr
    assert "credential: MoonieX-SomPong/prod/drive-share in Infisical (no file)" in result.stdout
    assert "credential file" not in result.stdout


def test_install_without_root_and_without_dry_run_is_refused():
    import os
    if os.geteuid() == 0:
        import pytest
        pytest.skip("running as root: the root guard cannot be exercised")
    result = _bash(SCRIPT, "install")
    assert result.returncode == 1
    assert "needs root" in result.stderr
