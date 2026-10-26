"""Tests for scripts/cxo-claude.sh session ID adoption and resume UUID handling (Part B.1 & B.2).

Uses an isolated temp workspace with fake `tmux` and `claude` binaries so no real tmux server,
hub database, or Claude process is touched. Because cxo-claude.sh's EXIT trap cleans up lock/uuid
files when `claude` exits, the fake `claude` binary snapshots `state/locks/<role>-<sid>.uuid`,
environment variables, and argv while the launcher session is live.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_UUID = "d405e3e2-1111-2222-3333-a6f2f69c4825"


def _make_fake_root(tmp_path: Path) -> tuple[Path, Path]:
    fake_root = tmp_path / "core"
    fake_root.mkdir(parents=True)
    venv_bin = fake_root / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python").symlink_to(sys.executable)
    (venv_bin / "activate").write_text(f'export PATH="{Path(sys.executable).parent}:$PATH"\n')
    for name in ("lib", "policies", "config", "roles", "runners", "tools"):
        src = ROOT / name
        if src.exists():
            os.symlink(src, fake_root / name)

    scripts_dir = fake_root / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "cxo-claude.sh", scripts_dir / "cxo-claude.sh")
    launcher = scripts_dir / "cxo-claude.sh"
    launcher.write_text(launcher.read_text().replace(
        "ORG_FLAGS_DIR=/etc/org-flags", f"ORG_FLAGS_DIR={fake_root}/flags"))
    shutil.copy2(ROOT / "scripts" / "resolve-resume-id.sh", scripts_dir / "resolve-resume-id.sh")
    os.symlink(ROOT / "scripts" / "lib", scripts_dir / "lib")

    # No-op helper scripts so background hooks exit immediately without side effects.
    (scripts_dir / "hub").mkdir(parents=True)
    for rel in ("hub/org-python.sh", "tab-title.sh", "idle-ping-watcher.sh"):
        p = scripts_dir / rel
        p.write_text("#!/usr/bin/env bash\nexit 0\n")
        p.chmod(0o755)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)

    # Fake tmux returning $FAKE_TMUX_SESSION_NAME for `display-message -p '#S'`.
    fake_tmux = bin_dir / "tmux"
    fake_tmux.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >>\"$FAKE_TMUX_LOG\"\n"
        "if [ \"$1\" = has-session ]; then exit ${FAKE_TMUX_TAKEN:-1}; fi\n"
        "if [ \"$1\" = rename-session ]; then exit ${FAKE_TMUX_RENAME:-0}; fi\n"
        "if [ \"${1:-}\" = \"display-message\" ]; then\n"
        "  printf '%s\\n' \"${FAKE_TMUX_SESSION_NAME:-}\"\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n"
    )
    fake_tmux.chmod(0o755)

    # Fake claude that records env, argv, and the live state/locks/<role>-<sid>.uuid file.
    fake_claude = bin_dir / "claude"
    fake_claude.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, pathlib, sys\n"
        "root = pathlib.Path(os.environ['FAKE_CORE_ROOT'])\n"
        "role = os.environ.get('CXO_ROLE', '')\n"
        "sid = os.environ.get('CXO_SESSION_ID', '')\n"
        "uuid_path = root / 'state' / 'locks' / f'{role}-{sid}.uuid'\n"
        "data = {\n"
        "    'role': role,\n"
        "    'sid': sid,\n"
        "    'cto_sid': os.environ.get('CTO_SESSION_ID', ''),\n"
        "    'uuid_file_exists': uuid_path.exists(),\n"
        "    'uuid_file_content': uuid_path.read_text().strip() if uuid_path.exists() else None,\n"
        "    'argv': sys.argv[1:],\n"
        "}\n"
        "pathlib.Path(os.environ['FAKE_CLAUDE_OUT']).write_text(json.dumps(data))\n"
    )
    fake_claude.chmod(0o755)

    return fake_root, bin_dir


def _run_launcher(
    tmp_path: Path,
    args: list[str],
    *,
    tmux_session_name: str | None = None,
    taken: bool = False,
    rename_fail: bool = False,
) -> tuple[subprocess.CompletedProcess[str], dict]:
    fake_root, bin_dir = _make_fake_root(tmp_path)
    out_file = tmp_path / "claude_out.json"
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["FAKE_CORE_ROOT"] = str(fake_root)
    env["FAKE_TMUX_LOG"] = str(tmp_path / "tmux.log")
    env["FAKE_TMUX_TAKEN"] = "0" if taken else "1"
    env["FAKE_TMUX_RENAME"] = "1" if rename_fail else "0"
    env["FAKE_CLAUDE_OUT"] = str(out_file)
    env["CTO_CLAUDE_TEST_MODE"] = "1"
    env["ORG_HOST"] = "contabo"
    env["ORG_SINGLE_CLEVEL"] = "0"
    env["ORG_SESSION_SCOPE"] = "0"
    for k in ("CXO_SESSION_ID", "CTO_SESSION_ID", "CXO_ROLE", "TMUX"):
        env.pop(k, None)
    if tmux_session_name is not None:
        env["TMUX"] = "/tmp/tmux-0/default,123,0"
        env["FAKE_TMUX_SESSION_NAME"] = tmux_session_name

    proc = subprocess.run(
        ["bash", str(fake_root / "scripts" / "cxo-claude.sh"), *args],
        capture_output=True, text=True, env=env, cwd=str(fake_root),
    )
    captured = json.loads(out_file.read_text()) if out_file.exists() else {}
    return proc, captured


def test_fresh_tmux_rename(tmp_path):
    proc, cap = _run_launcher(tmp_path, ["--role", "cto"], tmux_session_name="cto-fresh")
    assert proc.returncode == 0
    assert f"rename-session -t cto-fresh -- cto-{cap['sid']}" in (tmp_path / "tmux.log").read_text()
    assert f"renamed tmux session 'cto-fresh' -> 'cto-{cap['sid']}'" in proc.stderr
    assert cap['uuid_file_content'].endswith(cap['sid'])


def test_rename_exclusions(tmp_path):
    for i, (name, args) in enumerate([
        ("cto-1a2b3c4d", []), ("cto-fresh", ["-r", SAMPLE_UUID]),
        ("cto-fresh", ["--session", "abcdef12"]), (None, []),
    ]):
        folder = tmp_path / str(i)
        proc, _ = _run_launcher(folder, ["--role", "cto", *args], tmux_session_name=name)
        assert proc.returncode == 0
        log = folder / "tmux.log"
        assert not log.exists() or "rename-session" not in log.read_text()


def test_rename_taken_and_failure_continue(tmp_path):
    for taken in (True, False):
        folder = tmp_path / str(taken)
        proc, cap = _run_launcher(folder, ["--role", "cto"], tmux_session_name="cto-fresh",
                                  taken=taken, rename_fail=not taken)
        assert proc.returncode == 0 and cap['uuid_file_exists']
        assert 'warning:' in proc.stderr
        assert ('rename-session' in (folder / 'tmux.log').read_text()) is not taken


def test_adopts_tmux_session_suffix_when_8_lowercase_hex(tmp_path):
    proc, cap = _run_launcher(tmp_path, ["--role", "cto"], tmux_session_name="cto-a1b2c3d4")
    assert proc.returncode == 0, proc.stderr
    assert cap["sid"] == "a1b2c3d4"
    assert cap["cto_sid"] == "a1b2c3d4"
    assert cap["uuid_file_exists"] is True
    assert cap["uuid_file_content"].endswith("a1b2c3d4")
    assert "not adopted" not in proc.stderr


def test_rejects_non_8_hex_tmux_suffix_mints_fresh_and_warns_stderr(tmp_path):
    proc, cap = _run_launcher(tmp_path, ["--role", "cto"], tmux_session_name="cto-fresh")
    assert proc.returncode == 0, proc.stderr
    assert cap["sid"] != "fresh"
    assert re.fullmatch(r"[0-9a-f]{8}", cap["sid"])
    assert "cto-fresh" in proc.stderr and "not adopted" in proc.stderr


def test_resume_sets_sid_from_uuid_last_8_hex_and_mints_fork_uuid(tmp_path):
    proc, cap = _run_launcher(
        tmp_path,
        ["--role", "cto", "-r", SAMPLE_UUID],
        tmux_session_name="cto-f69c4825",
    )
    assert proc.returncode == 0, proc.stderr
    assert cap["sid"] == "f69c4825"
    assert cap["cto_sid"] == "f69c4825"
    assert cap["uuid_file_exists"] is True
    assert cap["uuid_file_content"] != SAMPLE_UUID
    argv = cap["argv"]
    assert cap["uuid_file_content"].endswith("f69c4825")
    assert argv[argv.index("--session-id") + 1] == cap["uuid_file_content"]
    assert "--fork-session" in argv
    assert "-r" in argv and argv[argv.index("-r") + 1] == SAMPLE_UUID


def test_resume_respects_explicit_session_override(tmp_path):
    proc, cap = _run_launcher(
        tmp_path,
        ["--role", "cto", "--session", "req-12345678", "--resume", SAMPLE_UUID],
    )
    assert proc.returncode == 0, proc.stderr
    assert cap["sid"] == "req-12345678"
    assert cap["uuid_file_content"] != SAMPLE_UUID
