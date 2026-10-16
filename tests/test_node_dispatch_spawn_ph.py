"""A Project Head on winbox, started over the org mesh (M13c, HostSpawn).

A Contabo C-level runs `python -m tools.spawn_ph mesh --host winbox --project P`;
lib/mesh sends `spawn_ph <lane> <owner sid> <project>` to tools/node_dispatch on
winbox, which runs tools.spawn_ph.spawn_from_mesh and starts the window through a
one-shot interactive scheduled task.

Nothing here touches a real host, tmux, wt.exe, PowerShell, the hub or the
filesystem outside tmp_path: the scheduled task is `nd._run_powershell`, the audit
row and the hub slots are mocks, and every state directory is redirected.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from lib import mesh, org_flags, resource_gate
from tools import node_dispatch as nd
from tools import send_to_cxo as sc
from tools import spawn_ph
from tools.agent_transport import Identity

PH = "project_head"
OWNER = "c0ffee01"
HELD_SID = "ab12cd34"
LAUNCHER = r"C:\Users\x\repo\windows\cxo-claude.ps1"
STARTED = subprocess.CompletedProcess([], 0, "STARTED Running\n", "")

_ENV = ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID", "CTO_SESSION", "ORG_PH_ROLES",
        "ORG_PH_LANE", "ORG_PH_PROJECT", "ORG_PH_OWNER", "ORG_SPAWN_GATE",
        "WORKER_TASK_ID", "WORKER_CTO_ROLE", "WORKER_CTO_ID", "WORKER_ROLE")  # a worker runs these too


class Box:
    def __init__(self, tmp_path: Path):
        self.locks = tmp_path / "locks"
        self.briefs = tmp_path / "briefs"
        self.hold = tmp_path / "CEO_HOLD.json"
        self.powershell = Mock(return_value=STARTED)

    def claim_files(self) -> list[str]:
        return sorted(p.name for p in self.locks.glob(f"{PH}-*") if p.suffix in (".project", ".spawned_by"))


@pytest.fixture()
def box(tmp_path, monkeypatch):
    """winbox as the verb sees it: Windows, the flag on, no CEO hold, no PH yet."""
    for k in _ENV:
        monkeypatch.delenv(k, raising=False)
    b = Box(tmp_path)
    b.locks.mkdir()
    doc = tmp_path / "project_head.md"
    doc.write_text("role doc\n")
    monkeypatch.setenv("ORG_PH_ROLES", "1")
    monkeypatch.setattr(org_flags, "FLAGS_DIR", tmp_path / "etc-org-flags")
    monkeypatch.setattr(sc, "LOCKS_DIR", b.locks)
    monkeypatch.setattr(spawn_ph, "LOCKS_DIR", b.locks)
    monkeypatch.setattr(spawn_ph, "BRIEFS_DIR", b.briefs)
    monkeypatch.setattr(spawn_ph, "ROLE_DOC", doc)
    monkeypatch.setattr(spawn_ph, "CEO_HOLD", b.hold)
    monkeypatch.setattr(spawn_ph, "WIN_LAUNCHER", LAUNCHER)
    monkeypatch.setattr(spawn_ph.resource_gate, "check", lambda *a, **k: None)
    # Session 0 is where sshd puts this process; the scheduled task is what reaches the desktop.
    monkeypatch.setattr(spawn_ph, "_windows_session_id", lambda: 0)
    monkeypatch.setattr(nd, "_self_host", lambda: "winbox")
    monkeypatch.setattr(nd, "_is_windows", lambda: True)
    monkeypatch.setattr(nd, "_audit", Mock())
    monkeypatch.setattr(nd, "_claim", Mock(return_value="token"))
    monkeypatch.setattr(nd, "_release", Mock())
    monkeypatch.setattr(nd, "_run_powershell", b.powershell)
    return b


def run(*args: str):
    return nd._run("spawn_ph", list(args))


def ok(box) -> dict:
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 0, out
    return out["result"]


# --- the arguments ---

@pytest.mark.parametrize("args", [
    ("ceo", OWNER, "LuminaSkies"), ("CTO", OWNER, "LuminaSkies"), ("cto;id", OWNER, "LuminaSkies"),
    ("project_head", OWNER, "LuminaSkies"),                          # a PH owns no PH
    ("cto", "ABCD1234", "LuminaSkies"), ("cto", "abcd123", "LuminaSkies"),
    ("cto", "abcd12345", "LuminaSkies"), ("cto", "abcd123g", "LuminaSkies"),
    ("cto", "abcd123\u0664", "LuminaSkies"),
    ("cto", OWNER, "Lumina;Skies"), ("cto", OWNER, "Lumina Skies"), ("cto", OWNER, "-Lumina"),
    ("cto", OWNER, "a" * 41), ("cto", OWNER, ""), ("cto", OWNER, "../x"), ("cto", OWNER, "X\n"),
    ("cto", OWNER, "LuminaSkies", "extra"),                           # a 4th argument
    ("cto", OWNER), ("cto",), (),
])
def test_a_bad_argument_is_refused_before_anything_runs(box, monkeypatch, args):
    spawn = Mock()
    monkeypatch.setattr(spawn_ph, "spawn_from_mesh", spawn)
    out, code = run(*args)
    assert (code, out["ok"]) == (2, False), out
    spawn.assert_not_called()
    box.powershell.assert_not_called()
    nd._claim.assert_not_called()
    assert box.claim_files() == []


def test_the_arguments_are_checked_by_the_dispatching_side_too(monkeypatch):
    """lib.mesh.build_argv runs node_dispatch's own check, so a bad call never reaches ssh."""
    monkeypatch.setattr(mesh, "mesh_destination", lambda host: "ops@winbox.example")
    argv = mesh.build_argv("winbox", "spawn_ph", ["cto", OWNER, "LuminaSkies"])
    assert argv[-1] == f"spawn_ph cto {OWNER} LuminaSkies"
    for bad in (["cto", OWNER, "a b"], ["cto", OWNER, "x;id"], ["ceo", OWNER, "X"],
                ["cto", "NOPE", "X"], ["cto", OWNER, "X", "y"]):
        with pytest.raises(nd.Refusal):
            mesh.build_argv("winbox", "spawn_ph", bad)


def test_the_mesh_waits_longer_than_the_scheduled_task_does():
    assert mesh.VERB_TIMEOUT_S["spawn_ph"] >= mesh.CONNECT_TIMEOUT_S + nd._SCHTASK_TIMEOUT_S


# --- the gates ---

@pytest.mark.parametrize("os_name", ["linux", "darwin"])
def test_other_systems_are_refused(box, monkeypatch, os_name):
    monkeypatch.setattr(nd, "_is_windows", lambda: False)
    monkeypatch.setattr(nd, "_os_name", lambda: os_name)
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 2
    assert out["error"] == "spawn_ph over the mesh is winbox-only; Linux/Mac spawn locally or by card"
    nd._claim.assert_not_called()
    box.powershell.assert_not_called()
    assert box.claim_files() == []


def test_the_flag_off_is_refused(box, monkeypatch):
    monkeypatch.delenv("ORG_PH_ROLES")
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 2 and "Project Heads are off on this host" in out["error"]
    box.powershell.assert_not_called()
    assert box.claim_files() == []


def test_the_flag_file_turns_it_on_without_the_env(box, monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_PH_ROLES")
    flags = tmp_path / "etc-org-flags"
    flags.mkdir()
    (flags / "ORG_PH_ROLES").write_text("")
    ok(box)


def test_a_project_already_held_is_refused_ignoring_case(box):
    (box.locks / f"{PH}-{HELD_SID}.project").write_text("LuminaSkies")   # a claim younger than the grace
    out, code = run("cto", OWNER, "luminaskies")
    assert code == 2 and f"already has a live Project Head #{HELD_SID}" in out["error"]
    box.powershell.assert_not_called()
    assert box.claim_files() == [f"{PH}-{HELD_SID}.project"]          # the holder's claim is not touched


def test_another_project_is_not_blocked_by_a_held_one(box):
    (box.locks / f"{PH}-{HELD_SID}.project").write_text("Console")
    ok(box)


def test_a_missing_role_doc_and_the_resource_gate_refuse(box, monkeypatch, tmp_path):
    monkeypatch.setattr(spawn_ph, "ROLE_DOC", tmp_path / "missing.md")
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 2 and "COO writes it" in out["error"]
    monkeypatch.setattr(spawn_ph, "ROLE_DOC", tmp_path / "project_head.md")
    monkeypatch.setattr(spawn_ph.resource_gate, "check", lambda *a, **k: "RAM is low")
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 2 and out["error"] == "RAM is low"
    box.powershell.assert_not_called()


def test_the_ceo_hold_is_refused(box):
    box.hold.write_text("{}")
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 2 and "the CEO is using this PC" in out["error"]
    box.powershell.assert_not_called()
    assert box.claim_files() == []
    assert not box.briefs.exists()


def test_the_ceo_hold_check_stands_alone(tmp_path):
    hold = tmp_path / "CEO_HOLD.json"
    assert spawn_ph.ceo_hold_refusal(hold) is None
    hold.write_text("{}")
    assert "CEO is using this PC" in spawn_ph.ceo_hold_refusal(hold)
    # windows_refusal is the hold first, then session 0: the split changed neither.
    assert "CEO is using this PC" in spawn_ph.windows_refusal(0, hold)
    hold.unlink()
    assert "session 0" in spawn_ph.windows_refusal(0, hold)
    assert spawn_ph.windows_refusal(1, hold) is None


def test_session_0_does_not_refuse_the_mesh_path(box):
    """sshd's session is 0 and spawn() would refuse there; the scheduled task is what reaches session 1."""
    assert spawn_ph._windows_session_id() == 0
    ok(box)


def test_a_start_already_in_progress_is_refused(box):
    nd._claim.return_value = None
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 2 and "another start of project LuminaSkies" in out["error"]
    box.powershell.assert_not_called()


def test_the_slot_is_per_project_and_always_freed(box):
    ok(box)
    key = nd._claim.call_args.args[0]
    assert key == "ph:winbox:luminaskies:start"
    nd._release.assert_called_once_with(key, "token")
    nd._release.reset_mock()
    box.powershell.return_value = subprocess.CompletedProcess([], 1, "", "boom")
    run("cto", OWNER, "Console")
    nd._release.assert_called_once_with("ph:winbox:console:start", "token")


# --- what a start writes ---

def test_the_owner_record_and_the_claim(box):
    result = ok(box)
    sid = result["session_id"]
    assert result == {"session_id": sid, "project": "LuminaSkies", "owner": f"cto-{OWNER}",
                      "via": "schtask"}
    assert (box.locks / f"{PH}-{sid}.spawned_by").read_text() == f"cxo:cto:{OWNER}"
    assert (box.locks / f"{PH}-{sid}.project").read_text() == "LuminaSkies"
    # The same record spawn() writes, which is what lets the PH write to its owner and no one else.
    assert sc._owner_of(Identity("cxo", PH, sid)) == Identity("cxo", "cto", OWNER)


def test_the_brief_is_a_fixed_stub(box):
    sid = ok(box)["session_id"]
    assert (box.briefs / f"{PH}-{sid}.md").read_text() == (
        f"Your owner cto-{OWNER} sends your brief by message. Run /session-open once it arrives.\n")
    assert [p.name for p in box.briefs.iterdir()] == [f"{PH}-{sid}.md"]


def test_the_scheduled_task_runs_the_launcher_args(box):
    sid = ok(box)["session_id"]
    (script,), kwargs = box.powershell.call_args
    assert f"-TaskName 'mooniex-ph-{sid}'" in script
    assert (f"-Argument '-NoProfile -ExecutionPolicy Bypass -File {LAUNCHER} -Role {PH} "
            f"-Lane cto -Project LuminaSkies -Session {sid}'") in script
    assert "-LogonType Interactive" in script          # the desktop, not session 0
    # the same tokens as the wt tab spawn() opens
    tail = spawn_ph.windows_launch_argv(sid, "cto", "LuminaSkies", wt="wt", new_window=False)
    assert tail[tail.index("powershell") + 1:] == spawn_ph.windows_launcher_args(sid, "cto", "LuminaSkies")


def test_a_token_with_a_space_is_wrapped_in_double_quotes(box, monkeypatch):
    spaced = r"C:\Users\x y\repo\windows\cxo-claude.ps1"
    monkeypatch.setattr(spawn_ph, "WIN_LAUNCHER", spaced)
    ok(box)
    (script,), _ = box.powershell.call_args
    assert f'-File "{spaced}" -Role {PH}' in script


def test_a_second_start_for_the_same_project_is_refused(box):
    ok(box)
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 2 and "already has a live Project Head" in out["error"]
    assert box.powershell.call_count == 1


# --- a launch that fails ---

def test_a_failed_launch_removes_the_claim_files(box):
    box.powershell.return_value = subprocess.CompletedProcess([], 1, "", "task state is Ready")
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 1 and "scheduled task exit 1" in out["error"]
    assert box.claim_files() == []
    # The project is free again: the next call is not told it is held.
    box.powershell.return_value = STARTED
    ok(box)


def test_a_launch_that_never_says_started_is_a_failure(box):
    box.powershell.return_value = subprocess.CompletedProcess([], 0, "", "")
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 1 and box.claim_files() == []


def test_a_powershell_that_cannot_run_removes_the_claim_files(box):
    box.powershell.side_effect = OSError("no powershell")
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 1 and "scheduled task launch failed" in out["error"]
    assert box.claim_files() == []


@pytest.mark.parametrize("launcher", [r"C:\Users\x\$env\cxo-claude.ps1", r"C:\Users\x\a'b\cxo-claude.ps1",
                                      r"C:\Users\x\a;b\cxo-claude.ps1", r'C:\Users\x\a"b\cxo-claude.ps1',
                                      "C:\\Users\\x\\a\nb.ps1"])
def test_a_token_powershell_could_act_on_is_refused_not_escaped(box, monkeypatch, launcher):
    monkeypatch.setattr(spawn_ph, "WIN_LAUNCHER", launcher)
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 2 and "not safe to hand to PowerShell" in out["error"]
    box.powershell.assert_not_called()
    assert box.claim_files() == []


def test_a_claim_that_cannot_be_written_is_taken_back(box, monkeypatch):
    def broken(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(sc, "record_spawn", broken)
    out, code = run("cto", OWNER, "LuminaSkies")
    assert code == 1 and "disk full" in out["error"]
    assert box.claim_files() == []
    box.powershell.assert_not_called()


def test_spawn_from_mesh_takes_back_the_claim_for_any_error(box):
    def launch(sid, args):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        spawn_ph.spawn_from_mesh("LuminaSkies", "cto", OWNER, launch=launch)
    assert box.claim_files() == []


def test_spawn_from_mesh_checks_its_own_arguments(box):
    never = Mock()
    for lane, sid, project in (("ceo", OWNER, "X"), ("cto", "NOPE", "X"), ("cto", OWNER, "a b"),
                               ("cto", OWNER, ""), ("project_head", OWNER, "X")):
        with pytest.raises(spawn_ph.Refused):
            spawn_ph.spawn_from_mesh(project, lane, sid, launch=never)
    never.assert_not_called()
    assert box.claim_files() == []


# --- spawn() still writes and cleans up the same way (the shared code moved) ---

def test_spawn_still_takes_back_its_files_when_the_launch_fails(box, monkeypatch):
    from tools import tmux_session
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CTO_SESSION_ID", OWNER)
    monkeypatch.setattr(spawn_ph.os, "name", "posix")
    monkeypatch.setattr(tmux_session, "create", Mock(side_effect=RuntimeError("no tmux")))
    with pytest.raises(spawn_ph.Refused, match="tmux spawn failed"):
        spawn_ph.spawn("LuminaSkies", "a brief")
    assert box.claim_files() == []
    assert [p.read_text() for p in box.briefs.iterdir()] == ["a brief"]


# --- the dispatching side: python -m tools.spawn_ph mesh ---

@pytest.fixture()
def clevel(box, monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CTO_SESSION_ID", OWNER)
    dispatch = Mock(return_value={"ok": True, "verb": "spawn_ph", "result": {
        "session_id": "11112222", "project": "LuminaSkies", "owner": f"cto-{OWNER}", "via": "schtask"}})
    monkeypatch.setattr(mesh, "dispatch", dispatch)
    return dispatch


def test_the_mesh_command_builds_the_dispatch_from_the_callers_identity(clevel, capsys):
    assert spawn_ph.main(["mesh", "--host", "winbox", "--project", "LuminaSkies"]) == 0
    clevel.assert_called_once_with("winbox", "spawn_ph", "cto", OWNER, "LuminaSkies")
    (line,) = capsys.readouterr().out.splitlines()
    assert json.loads(line)["result"]["via"] == "schtask"


def test_the_mesh_command_dry_run_sends_nothing(clevel, capsys):
    assert spawn_ph.main(["mesh", "--host", "winbox", "--project", "LuminaSkies", "--dry-run"]) == 0
    clevel.assert_not_called()
    (line,) = capsys.readouterr().out.splitlines()
    assert json.loads(line) == {"host": "winbox", "verb": "spawn_ph",
                                "args": ["cto", OWNER, "LuminaSkies"], "dry_run": True}


@pytest.mark.parametrize("env", [
    {},                                                                    # a bare shell
    {"CXO_ROLE": PH, "CXO_SESSION_ID": "11112222"},                       # a Project Head
    {"CXO_ROLE": "cto"},                                                  # a C-level with no session
])
def test_the_mesh_command_needs_a_c_level(box, monkeypatch, capsys, env):
    dispatch = Mock()
    monkeypatch.setattr(mesh, "dispatch", dispatch)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    for extra in ([], ["--dry-run"]):
        assert spawn_ph.main(["mesh", "--host", "winbox", "--project", "LuminaSkies", *extra]) == 1
        err = capsys.readouterr()
        assert err.out == "" and "spawn-ph mesh:" in err.err
    dispatch.assert_not_called()


def test_the_mesh_command_has_no_flag_for_the_lane_or_the_owner(clevel, capsys):
    for flag in (["--lane", "cmo"], ["--owner", "deadbeef"], ["--brief", "do this"]):
        with pytest.raises(SystemExit) as e:
            spawn_ph.main(["mesh", "--host", "winbox", "--project", "LuminaSkies", *flag])
        assert e.value.code == 2
    clevel.assert_not_called()


def test_the_mesh_command_takes_winbox_only(clevel):
    with pytest.raises(SystemExit):
        spawn_ph.main(["mesh", "--host", "mac", "--project", "LuminaSkies"])
    clevel.assert_not_called()


@pytest.mark.parametrize("project", ["../x", "a b", "x;id", "", "-x", "a" * 41])
def test_the_mesh_command_refuses_a_bad_project_before_dialling(clevel, capsys, project):
    assert spawn_ph.main(["mesh", "--host", "winbox", f"--project={project}"]) == 1
    assert "project must be" in capsys.readouterr().err
    clevel.assert_not_called()


def test_the_mesh_command_refuses_an_owner_session_the_verb_could_not_take(clevel, monkeypatch, capsys):
    monkeypatch.setenv("CTO_SESSION_ID", "main-session")           # send_to_cxo accepts it; the verb needs 8 hex
    assert spawn_ph.main(["mesh", "--host", "winbox", "--project", "LuminaSkies"]) == 1
    assert "8 lowercase hex" in capsys.readouterr().err
    clevel.assert_not_called()


def test_the_mesh_command_reports_an_unanswered_host_and_a_refusal(clevel, capsys):
    clevel.side_effect = mesh.MeshUnreachable("ssh failed")
    assert spawn_ph.main(["mesh", "--host", "winbox", "--project", "LuminaSkies"]) == 1
    assert "winbox did not answer over the mesh: ssh failed" in capsys.readouterr().err
    clevel.side_effect = None
    clevel.return_value = {"ok": False, "verb": "spawn_ph", "error": "the CEO is using this PC"}
    assert spawn_ph.main(["mesh", "--host", "winbox", "--project", "LuminaSkies"]) == 1
    (line,) = capsys.readouterr().out.splitlines()
    assert json.loads(line)["error"] == "the CEO is using this PC"
