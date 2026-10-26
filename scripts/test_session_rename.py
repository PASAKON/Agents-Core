"""scripts/session-rename.sh after M10b (Agents-Core #272): it sends a rename
request to tools/rename_service.py over its unix socket and never touches tmux.

The script runs from a staged root (its own copy, lib/tools/config/policies linked
from the repo) with a fake `tmux` first on PATH that logs any call: the log must
stay empty in every test. A stand-in service on a socket under /tmp
(RENAME_SERVICE_SOCK) records each request and answers "queued".

Run via:   pytest scripts/test_session_rename.py
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
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

    sock = Path("/tmp") / f"sr-test-{os.getpid()}-{id(tmp_path)}.sock"
    sock.unlink(missing_ok=True)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock))
    srv.listen(8)
    srv.settimeout(0.2)
    requests, stop = [], threading.Event()

    def serve():
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except OSError:
                continue
            with conn:
                buf = b""
                while chunk := conn.recv(4096):
                    buf += chunk
                req = json.loads(buf)
                requests.append(req)
                conn.sendall(f"queued {req['role']}-{req['sid']}: x\n".encode())

    t = threading.Thread(target=serve, daemon=True)
    t.start()

    def run(*args, role="cto", sid="c34459eb", host="contabo", extra=None):
        env = dict(os.environ)
        env.update(PATH=f"{bin_dir}:{env.get('PATH', '')}", TMUX="/tmp/fake,1,0",
                   CXO_ROLE=role, ORG_HOST=host, RENAME_SERVICE_SOCK=str(sock))
        env.pop("CXO_SESSION_ID", None)
        env.pop("CTO_SESSION_ID", None)
        if sid:
            env["CTO_SESSION_ID"] = sid
        env.update(extra or {})
        return subprocess.run(["bash", str(script), *args], env=env, capture_output=True,
                              text=True, timeout=30)

    run.root, run.log, run.requests, run.sock = root, log, requests, sock
    yield run
    stop.set()
    t.join(2)
    srv.close()
    sock.unlink(missing_ok=True)


def _req(run):
    return run.requests[-1]


def _no_tmux(run):
    assert not run.log.exists(), run.log.read_text()


def test_a_request_is_sent_and_tmux_is_never_called(stage):
    r = stage("ดูแล org")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith(f"requested: /rename {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — ดูแล org")
    assert _req(stage) == {"role": "cto", "sid": "c34459eb", "topic": "ดูแล org", "prefix": ""}
    assert not (stage.root / "state" / "rename-requests").exists()
    assert (stage.root / "state" / "locks" / "cto-c34459eb.topic").read_text() == "ดูแล org"
    _no_tmux(stage)


def test_same_topic_twice_is_a_noop_and_force_or_a_new_prefix_asks_again(stage):
    stage("x")
    assert stage("x").stdout.strip() == "unchanged: x"
    assert stage("--force", "x").stdout.startswith("requested:")
    r = stage("--prefix", "⏸", "x")
    assert r.stdout.startswith(f"requested: /rename ⏸ {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — x")
    assert stage("--show").stdout.strip() == "recorded: ⏸ x"
    _no_tmux(stage)


@pytest.mark.parametrize("host,lead", [("contabo", CONTABO + " CTO"), ("mac", MAC + " CTO"),
                                       ("winbox", WINBOX + " CTO"), ("bogus", "CTO")])
def test_the_host_emoji_comes_from_self_host(stage, host, lead):
    assert stage("t", host=host).stdout.startswith(f"requested: /rename {lead} (\U0001F468\u200d\U0001F4BB: Kavin) — t")


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
    assert stage.requests == []
    _no_tmux(stage)


def test_with_no_service_it_says_so_and_records_nothing(stage):
    r = stage("x", extra={"RENAME_SERVICE_SOCK": "/tmp/no-such-rename.sock"})
    assert r.returncode == 0
    assert r.stdout.startswith("not requested (rename service not reachable")
    assert r.stdout.rstrip().endswith(f"rename by hand: /rename {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — x")
    assert not (stage.root / "state" / "locks" / "cto-c34459eb.topic").exists()   # the next call tries again
    _no_tmux(stage)
