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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_UUID = "d405e3e2-1111-2222-3333-a6f2f69c4825"


def _make_fake_root(tmp_path: Path) -> tuple[Path, Path]:
    fake_root = tmp_path / "core"
    fake_root.mkdir(parents=True)
    for name in (".venv", "lib", "policies", "config", "roles", "runners", "tools"):
        src = ROOT / name
        if src.exists():
            os.symlink(src, fake_root / name)

    scripts_dir = fake_root / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "cxo-claude.sh", scripts_dir / "cxo-claude.sh")
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
) -> tuple[subprocess.CompletedProcess[str], dict]:
    fake_root, bin_dir = _make_fake_root(tmp_path)
    out_file = tmp_path / "claude_out.json"
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["FAKE_CORE_ROOT"] = str(fake_root)
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


def test_resume_sets_sid_from_uuid_last_8_hex_and_preserves_uuid(tmp_path):
    proc, cap = _run_launcher(
        tmp_path,
        ["--role", "cto", "-r", SAMPLE_UUID],
        tmux_session_name="cto-f69c4825",
    )
    assert proc.returncode == 0, proc.stderr
    assert cap["sid"] == "f69c4825"
    assert cap["cto_sid"] == "f69c4825"
    assert cap["uuid_file_exists"] is True
    assert cap["uuid_file_content"] == SAMPLE_UUID
    argv = cap["argv"]
    assert argv[argv.index("--session-id") + 1] == SAMPLE_UUID
    assert "-r" in argv and argv[argv.index("-r") + 1] == SAMPLE_UUID


def test_resume_respects_explicit_session_override(tmp_path):
    proc, cap = _run_launcher(
        tmp_path,
        ["--role", "cto", "--session", "req-12345678", "--resume", SAMPLE_UUID],
    )
    assert proc.returncode == 0, proc.stderr
    assert cap["sid"] == "req-12345678"
    assert cap["uuid_file_content"] == SAMPLE_UUID
