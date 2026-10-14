"""The CEO identity fallback in tools/agent_transport.current_identity()
(LungNote 09d85a20, phase 1).

A process with no CXO_ROLE / WORKER_TASK_ID / CTO_SESSION_ID used to be the
CEO, silently. Now: ORG_CEO_CALLER=1 is the CEO on purpose; anything else is
still the CEO while ORG_IDENTITY_STRICT is off, but leaves one line in
state/reports/identity-fallback.jsonl, and is refused once the flag is on.
Every other identity branch is unchanged.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.agent_transport as agent_transport  # noqa: E402
from lib import org_flags  # noqa: E402
from tools.agent_transport import CEO_IDENTITY, PH_ROLE, Identity  # noqa: E402

DEFAULT_LOG = agent_transport.IDENTITY_FALLBACK_LOG  # read before any fixture repoints it
FIELDS = {"ts", "pid", "ppid", "parent_comm", "exe", "script", "cwd_in_repo", "host"}
SENTINEL = "brief-sentinel-7f3a91"

_ENV = ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID", "CTO_SESSION", "WORKER_TASK_ID",
        "WORKER_ROLE", "ORG_PH_LANE", "ORG_CEO_CALLER", "ORG_IDENTITY_STRICT")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    for k in _ENV:
        monkeypatch.delenv(k, raising=False)
    flags = tmp_path / "org-flags"
    flags.mkdir()
    monkeypatch.setattr(org_flags, "FLAGS_DIR", flags)  # the host's /etc/org-flags never applies
    log = tmp_path / "reports" / "identity-fallback.jsonl"  # parent does not exist yet
    monkeypatch.setattr(agent_transport, "IDENTITY_FALLBACK_LOG", log)
    monkeypatch.setattr(agent_transport, "_fallback_recorded", False)
    return log


@pytest.fixture()
def log(isolated):
    return isolated


@pytest.fixture()
def strict(tmp_path):
    (tmp_path / "org-flags" / "ORG_IDENTITY_STRICT").touch()


def _lines(log: Path) -> list[dict]:
    if not log.exists():
        return []
    return [json.loads(x) for x in log.read_text().splitlines()]


def test_default_log_path_is_in_the_repo():
    assert DEFAULT_LOG == ROOT / "state" / "reports" / "identity-fallback.jsonl"


def test_no_identity_flag_off_is_ceo_and_logs_one_line(log, monkeypatch, tmp_path):
    argv0 = str(ROOT / "tools" / "send_to_cxo.py")
    monkeypatch.setattr(sys, "argv", [argv0, "--from", "x", "zz-target-zz", SENTINEL])
    monkeypatch.setenv("ORG_TEST_SENTINEL_VAR", SENTINEL)
    private = tmp_path / "private-cwd-9c2e"
    private.mkdir()
    monkeypatch.chdir(private)

    assert agent_transport.current_identity() == CEO_IDENTITY

    raw = log.read_text()
    assert SENTINEL not in raw and "--from" not in raw and "zz-target-zz" not in raw
    assert "private-cwd-9c2e" not in raw
    (line,) = _lines(log)
    assert set(line) == FIELDS
    assert line["pid"] == os.getpid()
    assert line["ppid"] == os.getppid()
    assert line["exe"] == "send_to_cxo.py"
    assert line["script"] == argv0
    assert line["cwd_in_repo"] is False
    assert isinstance(line["host"], str) and line["host"]
    assert line["ts"].endswith("+00:00")
    comm = Path(f"/proc/{os.getppid()}/comm")
    if comm.exists():
        assert line["parent_comm"] == comm.read_text().strip()
    else:
        assert line["parent_comm"] is None
    assert stat.S_IMODE(log.stat().st_mode) == 0o600


def test_script_is_null_outside_the_repo(log, monkeypatch, tmp_path):
    outside = tmp_path / "cron-job.py"
    outside.write_text("")
    monkeypatch.setattr(sys, "argv", [str(outside), SENTINEL])
    monkeypatch.chdir(ROOT)
    agent_transport.current_identity()
    (line,) = _lines(log)
    assert line["exe"] == "cron-job.py"
    assert line["script"] is None
    assert line["cwd_in_repo"] is True
    assert SENTINEL not in log.read_text()


def test_script_is_null_when_argv0_is_not_a_file(log, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["-c", SENTINEL])
    monkeypatch.chdir(ROOT)
    agent_transport.current_identity()
    (line,) = _lines(log)
    assert line["exe"] == "-c"
    assert line["script"] is None


@pytest.mark.parametrize("how", ["file", "env"])
def test_no_identity_flag_on_is_refused_and_still_logged(log, monkeypatch, tmp_path, how):
    if how == "file":
        (tmp_path / "org-flags" / "ORG_IDENTITY_STRICT").touch()
    else:
        monkeypatch.setenv("ORG_IDENTITY_STRICT", "1")
    with pytest.raises(PermissionError, match="ORG_IDENTITY_STRICT, LungNote 09d85a20"):
        agent_transport.current_identity()
    (line,) = _lines(log)
    assert set(line) == FIELDS


def test_flag_env_zero_does_not_turn_the_file_off(log, monkeypatch, strict):
    monkeypatch.setenv("ORG_IDENTITY_STRICT", "0")
    with pytest.raises(PermissionError):
        agent_transport.current_identity()


@pytest.mark.parametrize("flag_on", [False, True])
def test_ceo_caller_marker_is_ceo_and_not_logged(log, monkeypatch, tmp_path, flag_on):
    if flag_on:
        (tmp_path / "org-flags" / "ORG_IDENTITY_STRICT").touch()
    monkeypatch.setenv("ORG_CEO_CALLER", "1")
    assert agent_transport.current_identity() == CEO_IDENTITY
    assert not log.exists()
    assert not log.parent.exists()


@pytest.mark.parametrize("value", ["true", "yes", "0", "", " 1", "1 "])
def test_only_exactly_1_is_the_marker(log, monkeypatch, value):
    monkeypatch.setenv("ORG_CEO_CALLER", value)
    assert agent_transport.current_identity() == CEO_IDENTITY
    assert len(_lines(log)) == 1


# --- every other branch: same identity as before, flag on or off, never logged ---

@pytest.mark.parametrize("flag_on", [False, True])
@pytest.mark.parametrize("env, expected", [
    ({"CXO_ROLE": "cto", "CXO_SESSION_ID": "c0ffee01"}, Identity("cxo", "cto", "c0ffee01")),
    ({"CXO_ROLE": "cmo", "CXO_SESSION_ID": "ef04792e"}, Identity("cxo", "cmo", "ef04792e")),
    ({"CXO_ROLE": "cto", "CTO_SESSION_ID": "abc12345"}, Identity("cxo", "cto", "abc12345")),
    ({"CXO_ROLE": PH_ROLE, "CXO_SESSION_ID": "7cf528f0"}, Identity("cxo", PH_ROLE, "7cf528f0")),
    ({"WORKER_TASK_ID": "task-afe57b21", "WORKER_ROLE": "security_engineer"},
     Identity("dev", "security_engineer", "task-afe57b21")),
    ({"WORKER_TASK_ID": "task-afe57b21"}, Identity("dev", "dev", "task-afe57b21")),
    ({"CTO_SESSION_ID": "c34459eb"}, Identity("cxo", "cto", "c34459eb")),
])
def test_other_identity_branches_unchanged(log, monkeypatch, tmp_path, env, expected, flag_on):
    if flag_on:
        (tmp_path / "org-flags" / "ORG_IDENTITY_STRICT").touch()
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert agent_transport.current_identity() == expected
    assert not log.exists()


@pytest.mark.parametrize("flag_on", [False, True])
def test_ph_without_session_id_still_refused_by_its_own_branch(log, monkeypatch, tmp_path, flag_on):
    if flag_on:
        (tmp_path / "org-flags" / "ORG_IDENTITY_STRICT").touch()
    monkeypatch.setenv("CXO_ROLE", PH_ROLE)
    monkeypatch.setenv("CTO_SESSION_ID", "c0ffee01")
    with pytest.raises(PermissionError, match="no CXO_SESSION_ID"):
        agent_transport.current_identity()
    assert not log.exists()


# --- the log line itself ---

def test_second_call_in_the_same_process_writes_no_second_line(log):
    agent_transport.current_identity()
    agent_transport.current_identity()
    agent_transport.current_identity()
    assert len(_lines(log)) == 1


def test_second_call_with_the_flag_on_writes_no_second_line(log, strict):
    for _ in range(2):
        with pytest.raises(PermissionError):
            agent_transport.current_identity()
    assert len(_lines(log)) == 1


def test_appends_to_an_existing_log(log):
    log.parent.mkdir(parents=True)
    log.write_text('{"earlier": 1}\n')
    agent_transport.current_identity()
    lines = _lines(log)
    assert lines[0] == {"earlier": 1} and set(lines[1]) == FIELDS


def test_symlinked_log_is_not_followed(log, tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("keep\n")
    log.parent.mkdir(parents=True)
    log.symlink_to(target)
    assert agent_transport.current_identity() == CEO_IDENTITY
    assert target.read_text() == "keep\n"
    assert log.is_symlink()


def test_dangling_symlinked_log_creates_nothing(log, tmp_path):
    target = tmp_path / "would-be-created.txt"
    log.parent.mkdir(parents=True)
    log.symlink_to(target)
    assert agent_transport.current_identity() == CEO_IDENTITY
    assert not target.exists()


def test_symlinked_log_with_the_flag_on_still_refuses(log, tmp_path, strict):
    target = tmp_path / "target.txt"
    target.write_text("")
    log.parent.mkdir(parents=True)
    log.symlink_to(target)
    with pytest.raises(PermissionError):
        agent_transport.current_identity()
    assert target.read_text() == ""


def test_fifo_at_the_log_path_does_not_block(log):
    log.parent.mkdir(parents=True)
    os.mkfifo(log)
    out: list = []
    t = threading.Thread(target=lambda: out.append(agent_transport.current_identity()), daemon=True)
    t.start()
    t.join(5)
    assert not t.is_alive(), "opening a FIFO with no reader blocked current_identity()"
    assert out == [CEO_IDENTITY]


def test_log_over_the_cap_gets_no_line(log, monkeypatch):
    monkeypatch.setattr(agent_transport, "IDENTITY_FALLBACK_MAX_BYTES", 10)
    log.parent.mkdir(parents=True)
    log.write_text("x" * 11)
    assert agent_transport.current_identity() == CEO_IDENTITY
    assert log.read_text() == "x" * 11


def test_log_at_the_cap_still_gets_its_line(log, monkeypatch):
    monkeypatch.setattr(agent_transport, "IDENTITY_FALLBACK_MAX_BYTES", 10)
    log.parent.mkdir(parents=True)
    log.write_text("x" * 9 + "\n")
    agent_transport.current_identity()
    assert len(log.read_text().splitlines()) == 2


def test_cap_is_5_mb():
    assert agent_transport.IDENTITY_FALLBACK_MAX_BYTES == 5 * 1024 * 1024


def test_unwritable_log_dir_never_raises(log, monkeypatch, tmp_path):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("")
    monkeypatch.setattr(agent_transport, "IDENTITY_FALLBACK_LOG", blocker / "x.jsonl")
    assert agent_transport.current_identity() == CEO_IDENTITY


def test_a_failing_field_never_raises(log, monkeypatch):
    def boom():
        raise RuntimeError("no hostname")
    monkeypatch.setattr(agent_transport.socket, "gethostname", boom)
    assert agent_transport.current_identity() == CEO_IDENTITY


def test_a_failing_field_never_raises_with_the_flag_on(log, monkeypatch, strict):
    def boom():
        raise RuntimeError("no hostname")
    monkeypatch.setattr(agent_transport.socket, "gethostname", boom)
    with pytest.raises(PermissionError, match="no identity"):
        agent_transport.current_identity()
