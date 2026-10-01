"""cto-claude.sh / cxo-claude.sh take the machine label and HOST_KEY from
lib.config.self_host(), the resolver every Python tool uses. The old uname
guess labelled ANY Linux box with /opt/MoonieXHQ/Agents/Core "CONTABO" --
where deploy/join/join.sh puts a newly joined Linux node."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import shutil

import pytest

ROOT = Path(__file__).resolve().parent.parent
LAUNCHERS = ["scripts/cto-claude.sh", "scripts/cxo-claude.sh"]
BASH = shutil.which("bash") or "/bin/bash"
_BLOCK = re.compile(r'SELF_HOST_KEY="\$\(cd.*?\nif \[ -n "\$\{SELF_HOST_KEY:-\}" \]; then HOST_KEY="\$SELF_HOST_KEY"; fi\n', re.S)


def _run(launcher: str, env: dict) -> tuple[str, str]:
    block = _BLOCK.search((ROOT / launcher).read_text()).group(0)
    script = (f'set -euo pipefail\nROOT="{ROOT}"\n' + block
              + 'printf "%s %s\\n" "$MACHINE_LABEL" "$HOST_KEY"\n')
    r = subprocess.run([BASH, "-c", script], capture_output=True, text=True,
                       env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    label, key = r.stdout.split()
    return label, key


def _env(tmp_path, **extra) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "ORG_HOST"}
    env["HOME"] = str(tmp_path)
    env["PATH"] = f"{Path(sys.executable).parent}:{env.get('PATH', '')}"
    env.update(extra)
    return env


@pytest.mark.parametrize("launcher", LAUNCHERS)
def test_org_host_decides(launcher, tmp_path):
    assert _run(launcher, _env(tmp_path, ORG_HOST="contabo")) == ("CONTABO", "contabo")
    assert _run(launcher, _env(tmp_path, ORG_HOST="winbox")) == ("WINDOWS", "winbox")


@pytest.mark.parametrize("launcher", LAUNCHERS)
def test_a_joined_linux_node_is_not_called_contabo(launcher, tmp_path):
    node = tmp_path / ".config" / "mooniex"
    node.mkdir(parents=True)
    (node / "node.yaml").write_text("host: devbox\nos: linux\nhq_root: /opt/MoonieXHQ\n")
    assert _run(launcher, _env(tmp_path)) == ("DEVBOX", "devbox")


@pytest.mark.parametrize("launcher", LAUNCHERS)
def test_no_python_falls_back_to_the_uname_guess(launcher, tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for tool in ("uname", "hostname", "tr", "printf", "cat"):
        real = subprocess.run(["bash", "-c", f"command -v {tool}"], capture_output=True,
                              text=True).stdout.strip()
        if real.startswith("/"):
            (bindir / tool).symlink_to(real)
    env = _env(tmp_path)
    env["PATH"] = str(bindir)  # no python3 at all, and ROOT/.venv may not exist
    label, key = _run(launcher, env)
    assert key == {"MAC": "mac", "CONTABO": "contabo", "WINDOWS": "winbox"}.get(label, label.lower())
