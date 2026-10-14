"""scripts/session-rename.sh after M10b (Agents-Core #272): it writes a rename
request and never touches tmux; tools/rename_service.py applies it.

The script runs from a staged root (its own copy, lib/tools/config/policies linked
from the repo) with a fake `tmux` first on PATH that logs any call: the log must
stay empty in every test.

Run via:   pytest scripts/test_session_rename.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REAL_ROOT = Path(__file__).resolve().parent.parent
CONTABO, MAC, WINBOX = "\U0001F310", "\U0001F4BB", "\U0001F5A5️"


@pytest.fixture
def stage(tmp_path):
    root = tmp_path / "root"
    (root / "scripts").mkdir(parents=True)
    script = root / "scripts" / "session-rename.sh"
    script.write_text((REAL_ROOT / "scripts" / "session-rename.sh").read_text())
    for rel in ("lib", "tools", "config", "policies", "roles"):
        if (REAL_ROOT / rel).exists():
            (root / rel).symlink_to(REAL_ROOT / rel)
    (root / "scripts" / "lib").symlink_to(REAL_ROOT / "scripts" / "lib")
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "python").symlink_to(sys.executable)
    (root / "state" / "locks").mkdir(parents=True)
    bin_dir, log = tmp_path / "bin", tmp_path / "tmux.log"
    bin_dir.mkdir()
    (bin_dir / "tmux").write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{log}"\n')
    (bin_dir / "tmux").chmod(0o755)

    def run(*args, role="cto", sid="c34459eb", host="contabo", extra=None):
        env = dict(os.environ)
        env.update(PATH=f"{bin_dir}:{env.get('PATH', '')}", TMUX="/tmp/fake,1,0",
                   CXO_ROLE=role, ORG_HOST=host)
        env.pop("CXO_SESSION_ID", None)
        env.pop("CTO_SESSION_ID", None)
        if sid:
            env["CTO_SESSION_ID"] = sid
        env.update(extra or {})
        return subprocess.run(["bash", str(script), *args], env=env, capture_output=True,
                              text=True, timeout=30)

    run.root, run.log = root, log
    return run


def _req(run, box="cto-c34459eb"):
    return json.loads((run.root / "state" / "rename-requests" / f"{box}.json").read_text())


def _no_tmux(run):
    assert not run.log.exists(), run.log.read_text()


def test_a_request_is_written_and_tmux_is_never_called(stage):
    r = stage("ดูแล org")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith(f"requested: /rename {CONTABO} CTO (Kavin) — ดูแล org")
    assert _req(stage)["topic"] == "ดูแล org" and _req(stage)["prefix"] == ""
    assert (stage.root / "state" / "locks" / "cto-c34459eb.topic").read_text() == "ดูแล org"
    _no_tmux(stage)


def test_same_topic_twice_is_a_noop_and_force_or_a_new_prefix_asks_again(stage):
    stage("x")
    assert stage("x").stdout.strip() == "unchanged: x"
    assert stage("--force", "x").stdout.startswith("requested:")
    r = stage("--prefix", "⏸", "x")
    assert r.stdout.startswith(f"requested: /rename ⏸ {CONTABO} CTO (Kavin) — x")
    assert stage("--show").stdout.strip() == "recorded: ⏸ x"
    _no_tmux(stage)


@pytest.mark.parametrize("host,lead", [("contabo", CONTABO + " CTO"), ("mac", MAC + " CTO"),
                                       ("winbox", WINBOX + " CTO"), ("bogus", "CTO")])
def test_the_host_emoji_comes_from_self_host(stage, host, lead):
    assert stage("t", host=host).stdout.startswith(f"requested: /rename {lead} (Kavin) — t")


def test_a_ph_name_does_not_repeat_its_project(stage):
    locks = stage.root / "state" / "locks"
    (locks / "project_head-36c49776.project").write_text("MimiPage")
    (locks / "project_head-36c49776.spawned_by").write_text("cxo:cmo:ef04792e")
    r = stage("MimiPage", role="project_head", sid="36c49776")
    assert r.stdout.startswith(f"requested: /rename {CONTABO} PH#36c (CMO) - MimiPage (")
    r = stage("EP6 clip", role="project_head", sid="36c49776")
    assert r.stdout.startswith(f"requested: /rename {CONTABO} PH#36c (CMO) - MimiPage — EP6 clip")


def test_no_session_id_or_a_bad_prefix_requests_nothing(stage):
    r = stage("x", sid="")
    assert r.returncode == 0 and "nothing requested" in r.stdout
    r = stage("--prefix", "/exit", "x")
    assert r.returncode == 1 and "nothing requested" in r.stderr
    assert not (stage.root / "state" / "rename-requests" / "cto-c34459eb.json").exists()
    _no_tmux(stage)
