import json
import shlex

import pytest

from tools import clevel_gate, spawn_ph, tmux_session

@pytest.fixture(autouse=True)
def _no_hub_registry(monkeypatch):
    """spawn/resume bind the PH to its hub registry row; these tests have no hub."""
    monkeypatch.setattr(spawn_ph, "_register_project", lambda plan: plan.get("tier") or "normal")



SID = "12ab34cd"
NAME = f"project_head-{SID}"


@pytest.fixture
def locks(tmp_path, monkeypatch):
    monkeypatch.setattr(spawn_ph, "LOCKS_DIR", tmp_path)
    monkeypatch.setattr(tmux_session, "has_session", lambda name: False)
    monkeypatch.setattr(clevel_gate, "live_lock", lambda *a: None)
    monkeypatch.setattr(spawn_ph, "SPAWN_PROMPT_DELAY_S", 0)
    (tmp_path / f"{NAME}.project").write_text("Console")
    (tmp_path / f"{NAME}.spawned_by").write_text("cxo:cto:abcdef12")
    return tmp_path


def test_dry_run_preserves_identity_and_files(locks, capsys):
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in locks.iterdir()}
    assert spawn_ph.main(["--resume", SID, "--dry-run"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert {k: plan[k] for k in ("session_id", "tmux_session", "lane", "project", "owner")} == {
        "session_id": SID, "tmux_session": NAME, "lane": "cto",
        "project": "Console", "owner": "cto-abcdef12",
    }
    assert plan["dry_run"] is True
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in locks.iterdir()}


@pytest.mark.parametrize("suffix", ["project", "spawned_by"])
def test_missing_records(locks, suffix):
    (locks / f"{NAME}.{suffix}").unlink()
    with pytest.raises(spawn_ph.Refused, match=f"missing or unreadable.*{suffix}"):
        spawn_ph.resume(SID, dry_run=True)


def test_another_project_holder(locks, monkeypatch):
    monkeypatch.setattr(spawn_ph, "live_projects", lambda d: {"console": "deadbeef"})
    with pytest.raises(spawn_ph.Refused, match="live Project Head #deadbeef"):
        spawn_ph.resume_plan(SID)


def test_own_fresh_claim_cannot_mask_live_holder(locks, monkeypatch):
    (locks / "project_head-deadbeef.project").write_text("console")
    monkeypatch.setattr(spawn_ph, "live_projects", lambda d: {"console": SID})
    monkeypatch.setattr(clevel_gate, "live_sessions", lambda *a, **kw: [("deadbeef", 123)])
    with pytest.raises(spawn_ph.Refused, match="live Project Head #deadbeef"):
        spawn_ph.resume_plan(SID)


def test_invalid_owner_record(locks):
    (locks / f"{NAME}.spawned_by").write_text("cxo:project_head:abcdef12")
    with pytest.raises(spawn_ph.Refused, match="invalid spawned_by"):
        spawn_ph.resume_plan(SID)


def test_resume_cli_refusal(locks, capsys):
    (locks / f"{NAME}.project").unlink()
    assert spawn_ph.main(["--resume", SID, "--dry-run"]) == 1
    assert "missing or unreadable" in capsys.readouterr().err


@pytest.mark.parametrize("extra", [["--project", "Other"], ["--brief", "Go"],
                                  ["--from-card", "abc"], ["--brief-file", "/missing"]])
def test_resume_rejects_spawn_arguments(locks, extra):
    with pytest.raises(SystemExit) as exc:
        spawn_ph.main(["--resume", SID, *extra])
    assert exc.value.code == 2


@pytest.mark.parametrize("backend", ["tmux", "lock"])
def test_already_running(locks, monkeypatch, backend):
    if backend == "tmux":
        monkeypatch.setattr(tmux_session, "has_session", lambda name: name == NAME)
    else:
        monkeypatch.setattr(clevel_gate, "live_lock", lambda *a: 123)
    with pytest.raises(spawn_ph.Refused, match="already running"):
        spawn_ph.resume_plan(SID)


def test_resume_command_matches_spawn_exports():
    args = (SID, "cto", "Project ' quoted", "abcdef12")
    command = spawn_ph.resume_command(*args)
    assert command.split(" && ")[0] == spawn_ph.launch_command(*args, "hello").split(" && ")[0]
    tokens = shlex.split(command.split(" && ")[1])
    assert tokens[-2:] == ["--resume", SID]
    assert "--initial-prompt" not in tokens
    assert tokens[tokens.index("--project") + 1] == args[2]


@pytest.mark.parametrize("screen, dismissed", [("MCP server approval", True), ("Ready", False)])
def test_resume_creates_and_only_dismisses_mcp(locks, monkeypatch, screen, dismissed):
    created, keys = [], []
    monkeypatch.setattr(tmux_session, "create", lambda *a: created.append(a))
    monkeypatch.setattr(tmux_session, "capture", lambda *a: screen)
    monkeypatch.setattr(spawn_ph.subprocess, "run", lambda argv, **kw: keys.append(argv))
    result = spawn_ph.resume(SID)
    assert created == [(NAME, spawn_ph.ROOT, spawn_ph.resume_command(SID, "cto", "Console", "abcdef12"))]
    assert result["mcp_screen_dismissed"] is dismissed
    assert [k[-1] for k in keys] == (["Escape"] if dismissed else [])
    assert (locks / f"{NAME}.spawned_by").read_text() == "cxo:cto:abcdef12"


def test_failed_resume_keeps_records(locks, monkeypatch):
    def fail(*args):
        raise RuntimeError("failed")
    monkeypatch.setattr(tmux_session, "create", fail)
    with pytest.raises(spawn_ph.Refused, match="tmux resume failed"):
        spawn_ph.resume(SID)
    assert (locks / f"{NAME}.project").read_text() == "Console"
    assert (locks / f"{NAME}.spawned_by").read_text() == "cxo:cto:abcdef12"


@pytest.mark.parametrize("sid", ["../bad", "ABCDEF12", "123", ""])
def test_invalid_sid(locks, sid):
    with pytest.raises(spawn_ph.Refused, match="lowercase hex"):
        spawn_ph.resume_plan(sid)


def test_project_still_required():
    with pytest.raises(SystemExit) as exc:
        spawn_ph.main([])
    assert exc.value.code == 2
