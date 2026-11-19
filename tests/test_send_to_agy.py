"""Tests for tools/send_to_agy.py, scripts/live-sessions.sh AGY rows, and AGY <-> Claude routes."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from lib import db, mailbox, mesh
from tools import agy_card_run, mail_wake, send_to_agy

UUID_CONTABO_CLI = "64ad6099-0b86-45ae-9f48-fb1028fd2a55"
UUID_MAC_APP = "a753ef73-6f10-4c9c-a2c0-8b0e2088a111"
UUID_WINBOX_CLI = "11223344-5566-7788-99aa-bbccddeeff00"


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    db.init()


def _write_transcript(brain_dir: Path, conv_id: str, lines: list[dict[str, Any]]) -> Path:
    tfile = brain_dir / conv_id / ".system_generated" / "logs" / "transcript.jsonl"
    tfile.parent.mkdir(parents=True, exist_ok=True)
    tfile.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    return tfile


def test_scan_local_host_discovers_app_and_cli_conversations(tmp_path: Path) -> None:
    home = tmp_path / "home"
    app_brain = home / ".gemini" / "antigravity" / "brain"
    app_conv = home / ".gemini" / "antigravity" / "conversations"
    cli_brain = home / ".gemini" / "antigravity-cli" / "brain"
    cli_conv = home / ".gemini" / "antigravity-cli" / "conversations"
    sessions_dir = tmp_path / "agy-sessions"
    brains_dir = tmp_path / "ph-brains"

    _write_transcript(
        app_brain,
        UUID_MAC_APP,
        [
            {
                "type": "USER_INPUT",
                "source": "USER_EXPLICIT",
                "created_at": "2026-11-18T19:00:00Z",
                "content": (
                    "<USER_REQUEST>\n"
                    "Audit Mac Desktop App UI rendering and fix theme header\n"
                    "</USER_REQUEST>\n"
                    "Command Working Directory: /Users/gob/MoonieXHQ/Projects/MoonieX/Console"
                ),
            }
        ],
    )
    app_conv.mkdir(parents=True, exist_ok=True)
    (app_conv / f"{UUID_MAC_APP}.pb").write_bytes(b"pb-app")

    _write_transcript(
        cli_brain,
        UUID_CONTABO_CLI,
        [
            {
                "type": "USER_INPUT",
                "source": "USER_EXPLICIT",
                "created_at": "2026-11-18T20:30:00Z",
                "content": (
                    "# Task task-0d2258a9\n\n"
                    "Project: Mooniex Agents\n"
                    "Repo path (your worktree, work ONLY here): "
                    "/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-0d2258a9\n\n"
                    "## Description\n\n"
                    "CEO 19 Nov: Claude sessions and AGY sessions must message each other."
                ),
            }
        ],
    )
    cli_conv.mkdir(parents=True, exist_ok=True)
    (cli_conv / f"{UUID_CONTABO_CLI}.pb").write_bytes(b"pb-cli")

    convs = send_to_agy.scan_local_host(
        "mac",
        agents_root=tmp_path,
        home_dir=home,
        sessions_dir=sessions_dir,
        brains_dir=brains_dir,
        app_brain_dir=app_brain,
        app_conv_dir=app_conv,
        cli_brain_dir=cli_brain,
        cli_conv_dir=cli_conv,
    )

    by_id = {c["conversation_id"]: c for c in convs}
    assert set(by_id) == {UUID_MAC_APP, UUID_CONTABO_CLI}

    app_row = by_id[UUID_MAC_APP]
    assert app_row["host"] == "mac"
    assert app_row["app_vs_cli"] == "App"
    assert app_row["surface"] == "App"
    assert app_row["box"] == f"cto-agy-{UUID_MAC_APP[:8]}"
    assert app_row["cwd"] == "/Users/gob/MoonieXHQ/Projects/MoonieX/Console"
    assert "Audit Mac Desktop App UI rendering" in app_row["title"]
    assert app_row["first_user_line"] == app_row["title"]
    assert app_row["last_activity"] >= "2026-11-18T19:00:00Z"

    cli_row = by_id[UUID_CONTABO_CLI]
    assert cli_row["app_vs_cli"] == "CLI"
    assert cli_row["box"] == "developer-task-0d2258a9"
    assert cli_row["cwd"] == "/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-0d2258a9"
    assert "# Task task-0d2258a9" in cli_row["title"]
    assert "CEO 19 Nov" in cli_row["title"]


def test_list_conversations_scans_contabo_mac_winbox_with_ssh_mocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    cli_brain = home / ".gemini" / "antigravity-cli" / "brain"
    _write_transcript(
        cli_brain,
        UUID_CONTABO_CLI,
        [
            {
                "type": "USER_INPUT",
                "created_at": "2026-11-18T20:00:00Z",
                "content": "Contabo local AGY CLI conversation",
            }
        ],
    )

    mesh_calls: list[tuple[str, str, tuple[str, ...]]] = []

    def fake_dispatch(host: str, verb: str, *args: str, **kwargs: Any) -> dict[str, Any]:
        mesh_calls.append((host, verb, tuple(args)))
        assert (host, verb, args) == ("mac", "agy_list", ())
        return {
            "ok": True,
            "verb": "agy_list",
            "result": {
                "host": "mac",
                "conversations": [
                    {
                        "box": f"cto-agy-{UUID_MAC_APP[:8]}",
                        "uuid": UUID_MAC_APP,
                        "cwd": "/Users/gob/MoonieXHQ/Agents/Core",
                        "last_activity": "2026-11-18T21:00:00Z",
                        "title": "Mac Desktop App design review",
                        "surface": "App",
                    }
                ],
            },
        }

    ssh_calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        ssh_calls.append(list(cmd))
        ssh_target = cmd[5]
        if ssh_target == "winbox":
            payload = {
                "ok": True,
                "conversations": [
                    {
                        "box": f"cto-agy-{UUID_WINBOX_CLI[:8]}",
                        "host": "winbox",
                        "conversation_id": UUID_WINBOX_CLI,
                        "cwd": r"C:\Users\passg\mooniex\repo\MoonieX-Agents",
                        "last_activity": "2026-11-18T18:00:00Z",
                        "title": "Winbox MT5 watchdog check",
                        "app_vs_cli": "CLI",
                    }
                ],
            }
            return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr=f"unexpected ssh target {ssh_target!r}")

    monkeypatch.setattr(mesh, "dispatch", fake_dispatch)
    monkeypatch.setattr(send_to_agy.subprocess, "run", fake_run)

    data = send_to_agy.list_conversations(
        hosts=("contabo", "mac", "winbox"),
        env={"ORG_HOST": "contabo"},
        sessions_dir=tmp_path / "sessions",
        brains_dir=tmp_path / "brains",
        home_dir=home,
    )

    convs = data["conversations"]
    assert len(convs) == 3
    by_host = {c["host"]: c for c in convs}
    assert by_host["contabo"]["conversation_id"] == UUID_CONTABO_CLI
    assert by_host["contabo"]["app_vs_cli"] == "CLI"
    assert by_host["mac"]["conversation_id"] == UUID_MAC_APP
    assert by_host["mac"]["uuid"] == UUID_MAC_APP
    assert by_host["mac"]["app_vs_cli"] == "App"
    assert by_host["mac"]["surface"] == "App"
    assert by_host["winbox"]["conversation_id"] == UUID_WINBOX_CLI
    assert by_host["winbox"]["app_vs_cli"] == "CLI"

    assert mesh_calls == [("mac", "agy_list", ())]
    ssh_targets = {call[5] for call in ssh_calls}
    assert ssh_targets == {"winbox"}


def test_send_local_host_writes_letter_logs_cto_and_spawns_detached_agy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions_dir = tmp_path / "agy-sessions"
    inbox_root = tmp_path / "inbox"
    cto_log = tmp_path / "logs" / "cto.log"
    work_cwd = tmp_path / "worktree"
    work_cwd.mkdir(parents=True)

    agy_card_run.register_session(
        box="cto-agy-64ad6099",
        role="cto",
        conversation_id=UUID_CONTABO_CLI,
        cwd=work_cwd,
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "contabo"},
    )

    popen_calls: list[dict[str, Any]] = []

    class FakePopen:
        def __init__(self, cmd: list[str], **kwargs: Any) -> None:
            self.pid = 43210
            popen_calls.append({"cmd": list(cmd), "kwargs": kwargs})

    monkeypatch.setattr(send_to_agy.subprocess, "Popen", FakePopen)

    res = send_to_agy.send(
        "cto-agy-64ad6099",
        "Check PR #712 and confirm test results",
        from_box="cto-fresh",
        sessions_dir=sessions_dir,
        inbox_root=inbox_root,
        cto_log_path=cto_log,
        agy_bin="/root/.local/bin/agy",
        env={"ORG_HOST": "contabo"},
    )

    assert res["ok"] is True
    assert res["remote"] is False
    assert res["host"] == "contabo"
    assert res["box"] == "cto-agy-64ad6099"
    assert res["conversation_id"] == UUID_CONTABO_CLI
    assert res["from_box"] == "cto-fresh"
    assert res["pid"] == 43210

    # Verify letter written to state/inbox/<box>/ matches send_to_cxo shape
    letter_file = Path(res["letter_path"])
    assert letter_file.is_file()
    assert letter_file.parent == inbox_root / "cto-agy-64ad6099"
    letter_data = json.loads(letter_file.read_text(encoding="utf-8"))
    assert letter_data["from"] == {"role": "cto", "session_id": "fresh"}
    assert letter_data["to"] == {"role": "cto", "session_id": "agy-64ad6099"}
    assert letter_data["chain"] == ["cto:fresh", "cto:agy-64ad6099"]
    assert letter_data["body"] == "Check PR #712 and confirm test results"
    assert "sent_at" in letter_data

    # Verify detached Popen invocation and prompt instructions
    assert len(popen_calls) == 1
    cmd = popen_calls[0]["cmd"]
    kwargs = popen_calls[0]["kwargs"]
    assert cmd[0] == "/root/.local/bin/agy"
    assert "-p" in cmd
    assert "--conversation" in cmd
    conv_idx = cmd.index("--conversation")
    assert cmd[conv_idx + 1] == UUID_CONTABO_CLI

    prompt_arg = cmd[cmd.index("-p") + 1]
    assert "cto-fresh" in prompt_arg
    assert 'bash scripts/hub/org-python.sh tools/send_to_cxo.py cto-fresh "<reply>"' in prompt_arg
    assert (
        'bash scripts/hub/org-python.sh tools/send_to_agy.py reply cto-fresh "<reply>" --from cto-agy-64ad6099'
        in prompt_arg
    )
    assert kwargs.get("start_new_session") is True
    assert kwargs["env"]["AGY_CONVERSATION_ID"] == UUID_CONTABO_CLI
    assert kwargs["env"]["AGY_BOX"] == "cto-agy-64ad6099"
    assert kwargs["env"]["CXO_ROLE"] == "cto"
    assert kwargs["env"]["CXO_SESSION_ID"] == "agy-64ad6099"

    # Verify CTO event log entry
    assert cto_log.is_file()
    log_text = cto_log.read_text(encoding="utf-8")
    assert "[send_to_agy] cto-fresh (contabo) -> cto-agy-64ad6099" in log_text
    assert UUID_CONTABO_CLI in log_text


def test_send_remote_mac_and_winbox_resumes_over_ssh_with_host_map(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sessions_dir = tmp_path / "agy-sessions"
    inbox_root = tmp_path / "inbox"
    cto_log = tmp_path / "logs" / "cto.log"

    # Register one Mac App conversation and one Winbox CLI conversation
    mac_rec = agy_card_run.register_session(
        box=f"cto-agy-{UUID_MAC_APP[:8]}",
        role="cto",
        conversation_id=UUID_MAC_APP,
        cwd="/Users/gob/MoonieXHQ/Agents/Core",
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "mac"},
    )
    mac_rec["host"] = "mac"
    mac_rec["app_data_dir"] = "/Users/gob/.gemini/antigravity"
    (sessions_dir / f"cto-agy-{UUID_MAC_APP[:8]}.json").write_text(json.dumps(mac_rec), encoding="utf-8")

    win_rec = agy_card_run.register_session(
        box=f"cto-agy-{UUID_WINBOX_CLI[:8]}",
        role="cto",
        conversation_id=UUID_WINBOX_CLI,
        cwd=r"C:\Users\passg\mooniex\repo\MoonieX-Agents",
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "winbox"},
    )
    win_rec["host"] = "winbox"
    (sessions_dir / f"cto-agy-{UUID_WINBOX_CLI[:8]}.json").write_text(json.dumps(win_rec), encoding="utf-8")

    mesh_calls: list[tuple[str, str, tuple[str, ...]]] = []
    mesh_ok = True

    def fake_dispatch(host: str, verb: str, *args: str, **kwargs: Any) -> dict[str, Any]:
        mesh_calls.append((host, verb, tuple(args)))
        assert (host, verb) == ("mac", "deliver_letter")
        assert len(args) == 1 and args[0].isdigit()
        if not mesh_ok:
            return {
                "ok": False,
                "verb": "deliver_letter",
                "error": f"letter {args[0]} not delivered: no registered, unparked AGY session",
            }
        return {
            "ok": True,
            "verb": "deliver_letter",
            "result": {
                "letter_id": int(args[0]),
                "delivered": True,
                "to": f"cto-agy-{UUID_MAC_APP[:8]}",
                "woke": True,
            },
        }

    ssh_calls: list[dict[str, Any]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        ssh_calls.append({"cmd": list(cmd), "input": kwargs.get("input")})
        b64_arg = cmd[-1]
        decoded = json.loads(base64.b64decode(b64_arg.encode("ascii")).decode("utf-8"))
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "box": decoded["box"],
                    "conversation_id": decoded["conversation_id"],
                    "pid": 9876,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(mesh, "dispatch", fake_dispatch)
    monkeypatch.setattr(send_to_agy.subprocess, "run", fake_run)

    # 1. Send from Contabo to Mac App conversation by UUID -> routed through mesh.dispatch("mac", "deliver_letter")
    res_mac = send_to_agy.send(
        UUID_MAC_APP,
        "Please inspect the Mac Console layout",
        from_box="cto-fresh",
        sessions_dir=sessions_dir,
        inbox_root=inbox_root,
        cto_log_path=cto_log,
        env={"ORG_HOST": "contabo"},
    )
    assert res_mac["ok"] is True
    assert res_mac["remote"] is True
    assert res_mac["host"] == "mac"
    assert res_mac["app_vs_cli"] == "App"
    assert res_mac["woke"] is True
    assert res_mac["letter_path"] is None
    assert isinstance(res_mac["letter_id"], int)
    assert mesh_calls == [("mac", "deliver_letter", (str(res_mac["letter_id"]),))]
    assert ssh_calls == []

    letter_row = db.get_letter(res_mac["letter_id"])
    assert letter_row is not None
    assert (
        letter_row["to_host"],
        letter_row["to_role"],
        letter_row["to_session"],
        letter_row["from_role"],
        letter_row["from_session"],
        letter_row["from_host"],
        letter_row["body"],
    ) == (
        "mac",
        "cto",
        f"agy-{UUID_MAC_APP[:8]}",
        "cto",
        "fresh",
        "contabo",
        "Please inspect the Mac Console layout",
    )

    # 1b. Refused Mac letter: send_to_agy returns/prints the failure and does not write attempts/status to the DB
    mesh_ok = False
    res_refused = send_to_agy.send(
        UUID_MAC_APP,
        "Refused Mac message",
        from_box="cto-fresh",
        sessions_dir=sessions_dir,
        inbox_root=inbox_root,
        cto_log_path=cto_log,
        env={"ORG_HOST": "contabo"},
    )
    assert res_refused["ok"] is False
    assert "no registered, unparked AGY session" in res_refused["error"]
    refused_row = db.get_letter(res_refused["letter_id"])
    assert refused_row is not None
    assert (refused_row["status"], refused_row["attempts"], refused_row["last_error"]) == ("pending", 0, None)

    real_send = send_to_agy.send
    monkeypatch.setattr(send_to_agy, "send", lambda *a, **kw: res_refused)
    rc_refused = send_to_agy.main(["send", UUID_MAC_APP, "Refused Mac message", "--from", "cto-fresh"])
    assert rc_refused == 1
    assert "no registered, unparked AGY session" in capsys.readouterr().err
    monkeypatch.setattr(send_to_agy, "send", real_send)

    # 2. Send from Contabo to Winbox CLI conversation by box name -> stays on ssh winbox
    res_win = send_to_agy.send(
        f"cto-agy-{UUID_WINBOX_CLI[:8]}",
        "Check winbox disk fill",
        from_box="cto-fresh",
        sessions_dir=sessions_dir,
        inbox_root=inbox_root,
        cto_log_path=cto_log,
        env={"ORG_HOST": "contabo"},
    )
    assert res_win["ok"] is True
    assert res_win["remote"] is True
    assert res_win["host"] == "winbox"
    assert res_win["app_vs_cli"] == "CLI"
    assert len(ssh_calls) == 1
    win_cmd = ssh_calls[0]["cmd"]
    assert win_cmd[:6] == ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", "winbox"]


def test_render_live_sessions_adds_agy_rows_in_text_json_and_id_modes() -> None:
    sample_agy = [
        {
            "kind": "agy",
            "box": "cto-agy-64ad6099",
            "host": "contabo",
            "conversation_id": UUID_CONTABO_CLI,
            "uuid": UUID_CONTABO_CLI,
            "role": "cto",
            "session_id": "agy-64ad6099",
            "cwd": "/opt/MoonieXHQ/Agents/Core",
            "last_activity": "2026-11-18T21:00:00Z",
            "title": "Task task-0d2258a9 bidirectional messaging",
            "first_user_line": "Task task-0d2258a9 bidirectional messaging",
            "app_vs_cli": "CLI",
            "parked": False,
        },
        {
            "kind": "agy",
            "box": "cto-agy-a753ef73",
            "host": "mac",
            "conversation_id": UUID_MAC_APP,
            "uuid": UUID_MAC_APP,
            "role": "cto",
            "session_id": "agy-a753ef73",
            "cwd": "/Users/gob/MoonieXHQ/Agents/Core",
            "last_activity": "2026-11-18T20:45:00Z",
            "title": "Mac Desktop App session",
            "first_user_line": "Mac Desktop App session",
            "app_vs_cli": "App",
            "parked": False,
        },
    ]
    base_claude_text = (
        "LIVE SESSIONS — snapshot 10s old (1 live; address ONLY these)\n"
        "active   cto-fresh  (contabo)  CTO Main\n"
        "send (shell): bash scripts/hub/org-python.sh tools/send_to_cxo.py <role> \"<msg>\" "
        "| tools/send_to_worker.py <project_head-id> \"<msg>\""
    )

    rendered = send_to_agy.render_live_sessions_with_agy(
        [],
        agy_conversations=sample_agy,
        claude_text=base_claude_text,
    )
    assert "active   cto-fresh  (contabo)  CTO Main" in rendered
    assert "agy      cto-agy-64ad6099  (contabo CLI 64ad6099)  /opt/MoonieXHQ/Agents/Core" in rendered
    assert "agy      cto-agy-a753ef73  (mac App a753ef73)  /Users/gob/MoonieXHQ/Agents/Core" in rendered
    assert 'send (agy): bash scripts/hub/org-python.sh tools/send_to_agy.py send <box|uuid> "<msg>"' in rendered

    # JSON mode
    base_json = json.dumps({"generated_at": 1700000000, "host": "contabo", "sessions": []})
    rendered_json = send_to_agy.render_live_sessions_with_agy(
        ["--json"],
        agy_conversations=sample_agy,
        claude_text=base_json,
    )
    parsed = json.loads(rendered_json)
    assert len(parsed["sessions"]) == 2
    assert parsed["sessions"][0]["kind"] == "agy"
    assert parsed["sessions"][0]["status"] == "agy"
    assert parsed["sessions"][0]["box"] == "cto-agy-64ad6099"
    assert parsed["sessions"][1]["app_vs_cli"] == "App"

    # --id lookup when Claude snapshot returned "not live (no fresh row)"
    rendered_id = send_to_agy.render_live_sessions_with_agy(
        ["--id", "a753ef73"],
        agy_conversations=sample_agy,
        claude_text="not live (no fresh row)",
    )
    assert "agy      cto-agy-a753ef73  (mac App a753ef73)" in rendered_id


def test_reply_to_claude_from_contabo_mac_and_winbox(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions_dir = tmp_path / "agy-sessions"
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir(parents=True)
    inbox_root = tmp_path / "inbox"
    cto_log = tmp_path / "logs" / "cto.log"

    # 1. Local reply on Contabo: AGY session on Contabo -> cto-fresh on Contabo
    (locks_dir / "cto-fresh.lock").write_text("1234\n", encoding="utf-8")
    wake_calls: list[tuple[str, str]] = []

    def fake_wake(box: str, label: str = " Run ") -> dict[str, Any]:
        wake_calls.append((box, label))
        return {"action": "nudged", "target": box}

    monkeypatch.setattr(send_to_agy.mail_wake, "wake", fake_wake)

    local_res = send_to_agy.reply_to_claude(
        "cto-fresh",
        "Finished the Contabo verification",
        sessions_dir=sessions_dir,
        locks_dir=locks_dir,
        inbox_root=inbox_root,
        cto_log_path=cto_log,
        env={
            "ORG_HOST": "contabo",
            "AGY_CONVERSATION_ID": UUID_CONTABO_CLI,
        },
    )
    assert local_res["ok"] is True
    assert local_res["remote"] is False
    assert local_res["host"] == "contabo"
    assert local_res["to_box"] == "cto-fresh"
    assert local_res["from_box"] == f"project_head-agy-{UUID_CONTABO_CLI[:8]}"
    assert Path(local_res["letter_path"]).is_file()
    assert wake_calls == [("cto-fresh", f"project_head-agy-{UUID_CONTABO_CLI[:8]}")]

    # 2. Remote reply from Mac AGY session -> cto-fresh on Contabo over SSH
    ssh_calls: list[list[str]] = []

    def fake_ssh_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        ssh_calls.append(list(cmd))
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"ok": True, "to_box": "cto-fresh", "wake": {"action": "nudged"}}),
            stderr="",
        )

    monkeypatch.setattr(send_to_agy.subprocess, "run", fake_ssh_run)

    mac_res = send_to_agy.reply_to_claude(
        "cto-fresh",
        "Mac App check complete",
        sessions_dir=sessions_dir,
        locks_dir=tmp_path / "empty-locks",
        inbox_root=inbox_root,
        cto_log_path=cto_log,
        env={
            "ORG_HOST": "mac",
            "AGY_CONVERSATION_ID": UUID_MAC_APP,
        },
    )
    assert mac_res["ok"] is True
    assert mac_res["remote"] is True
    assert mac_res["host"] == "contabo"
    assert ssh_calls[-1][:6] == ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", "mooniex-vps"]

    # 3. Remote reply from Winbox AGY session -> cmo-a1b2c3d4 on Mac (using recorded last_from_host, via mesh)
    mesh_calls: list[tuple[str, str, tuple[str, ...]]] = []

    def fake_mesh_dispatch(host: str, verb: str, *args: str, **kwargs: Any) -> dict[str, Any]:
        mesh_calls.append((host, verb, tuple(args)))
        return {
            "ok": True,
            "verb": "deliver_letter",
            "result": {"letter_id": int(args[0]), "delivered": True, "to": "cmo-a1b2c3d4", "woke": True},
        }

    monkeypatch.setattr(mesh, "dispatch", fake_mesh_dispatch)

    win_box = f"cto-agy-{UUID_WINBOX_CLI[:8]}"
    win_rec = agy_card_run.register_session(
        box=win_box,
        role="cto",
        conversation_id=UUID_WINBOX_CLI,
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "winbox"},
    )
    win_rec["last_from"] = "cmo-a1b2c3d4"
    win_rec["last_from_host"] = "mac"
    (sessions_dir / f"{win_box}.json").write_text(json.dumps(win_rec), encoding="utf-8")

    win_res = send_to_agy.reply_to_claude(
        "cmo-a1b2c3d4",
        "Winbox build succeeded",
        from_box=win_box,
        sessions_dir=sessions_dir,
        locks_dir=tmp_path / "empty-locks",
        inbox_root=inbox_root,
        cto_log_path=cto_log,
        env={"ORG_HOST": "winbox"},
    )
    assert win_res["ok"] is True
    assert win_res["remote"] is True
    assert win_res["host"] == "mac"
    assert mesh_calls == [("mac", "deliver_letter", (str(win_res["letter_id"]),))]


def test_agy_card_run_wake_prompt_includes_reply_route_and_mail_wake_handles_standalone_agy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = agy_card_run.format_wake_prompt(
        "cto-agy-64ad6099",
        [
            {
                "from": {"role": "cto", "session_id": "fresh"},
                "sent_at": "2026-11-18T21:00:00Z",
                "body": "Please review the latest migration",
            }
        ],
    )
    assert 'bash scripts/hub/org-python.sh tools/send_to_cxo.py cto-fresh "<reply>"' in prompt
    assert (
        'bash scripts/hub/org-python.sh tools/send_to_agy.py reply cto-fresh "<reply>" --from cto-agy-64ad6099'
        in prompt
    )

    # Verify mail_wake.wake routes a standalone AGY box (not starting with cto-/project_head-) to handle_agy
    sessions_dir = tmp_path / "agy-sessions"
    inbox_root = tmp_path / "inbox"
    agy_card_run.register_session(
        box="agy-custombox1",
        role="agy",
        conversation_id=UUID_CONTABO_CLI,
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "contabo"},
    )
    mailbox.send(
        "agy",
        "custombox1",
        "Ping standalone AGY box",
        "cto",
        "fresh",
        root=inbox_root,
    )
    spawned_boxes: list[str] = []
    monkeypatch.setattr(mail_wake, "AGY_SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(agy_card_run, "AGY_SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(mailbox, "INBOX_ROOT", inbox_root)
    monkeypatch.setattr(
        mail_wake,
        "_spawn_agy_runner",
        lambda box: spawned_boxes.append(box),
    )

    res = mail_wake.wake("agy-custombox1", label="cto-fresh")
    assert res["woke"] is True
    assert res["box"] == "agy-custombox1"
    assert res["reason"] == mail_wake.AGY_REASON
    assert spawned_boxes == ["agy-custombox1"]


def test_cli_main_list_send_reply_and_error_codes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        send_to_agy,
        "list_conversations",
        lambda **kwargs: {
            "scanned_at": "2026-11-18T21:00:00Z",
            "hosts": {"contabo": {"ok": True, "conversations": []}},
            "conversations": [
                {
                    "kind": "agy",
                    "box": "cto-agy-64ad6099",
                    "host": "contabo",
                    "conversation_id": UUID_CONTABO_CLI,
                    "uuid": UUID_CONTABO_CLI,
                    "cwd": "/opt/MoonieXHQ/Agents/Core",
                    "last_activity": "2026-11-18T21:00:00Z",
                    "title": "Test CLI list",
                    "first_user_line": "Test CLI list",
                    "app_vs_cli": "CLI",
                }
            ],
        },
    )

    rc_table = send_to_agy.main(["list", "--host", "contabo"])
    assert rc_table == 0
    out_table = capsys.readouterr().out
    assert "CONVERSATION UUID" in out_table
    assert "cto-agy-64ad6099" in out_table
    assert UUID_CONTABO_CLI in out_table

    rc_json = send_to_agy.main(["list", "--local", "--json"])
    assert rc_json == 0
    parsed_list = json.loads(capsys.readouterr().out)
    assert parsed_list[0]["box"] == "cto-agy-64ad6099"

    monkeypatch.setattr(
        send_to_agy,
        "send",
        lambda target, msg, **kw: {
            "ok": True,
            "box": "cto-agy-64ad6099",
            "from_box": kw.get("from_box") or "cto-fresh",
            "host": "contabo",
            "conversation_id": UUID_CONTABO_CLI,
            "app_vs_cli": "CLI",
            "pid": 1111,
        },
    )
    rc_send = send_to_agy.main(["send", "cto-agy-64ad6099", "hello from cli", "--from", "cto-fresh"])
    assert rc_send == 0
    assert "sent to AGY cto-agy-64ad6099" in capsys.readouterr().out

    monkeypatch.setattr(
        send_to_agy,
        "reply_to_claude",
        lambda to_box, msg, **kw: {
            "ok": True,
            "from_box": kw.get("from_box") or "cto-agy-64ad6099",
            "to_box": to_box,
            "host": "contabo",
            "remote": False,
        },
    )
    rc_reply = send_to_agy.main(["reply", "cto-fresh", "ack from agy", "--from", "cto-agy-64ad6099"])
    assert rc_reply == 0
    assert "replied to cto-fresh on contabo" in capsys.readouterr().out

    def raise_not_found(*args: Any, **kwargs: Any) -> Any:
        raise send_to_agy.TargetNotFoundError("no AGY conversation found")

    monkeypatch.setattr(send_to_agy, "send", raise_not_found)
    rc_missing = send_to_agy.main(["send", "nonexistent-box", "hello"])
    assert rc_missing == 2



@pytest.mark.parametrize("surface", ["App", "CLI"])
def test_app_surface_wakes_through_app_store_and_hub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, surface: str,
) -> None:
    """A Mac App conversation is reachable only with --app_data_dir antigravity + AGY_ENABLE_HUB=1
    (live 2026-11-19: without them agy said "trajectory not found"); a CLI one keeps the plain call."""
    calls: list[dict[str, Any]] = []

    class FakePopen:
        def __init__(self, cmd: list[str], **kwargs: Any) -> None:
            self.pid = 1
            calls.append({"cmd": list(cmd), "env": kwargs["env"]})

    monkeypatch.setattr(send_to_agy.subprocess, "Popen", FakePopen)
    send_to_agy._spawn_detached_local_agy(
        "hello", box="cto-agy-1ec08f78", to_role="cto", to_sid="agy-1ec08f78",
        conversation_id=UUID_CONTABO_CLI, model="m", mode="plan", cwd=tmp_path,
        surface=surface, sessions_dir=tmp_path / "s", agy_bin="/bin/agy", env={},
    )
    cmd, env = calls[0]["cmd"], calls[0]["env"]
    if surface == "App":
        assert cmd[:3] == ["/bin/agy", "--app_data_dir", "antigravity"]
        assert env["AGY_ENABLE_HUB"] == "1"
    else:
        assert "--app_data_dir" not in cmd
        assert "AGY_ENABLE_HUB" not in env


def test_remote_script_app_wake_uses_app_store_and_hub() -> None:
    src = send_to_agy._REMOTE_AGY_PY
    assert 'cmd[1:1] = ["--app_data_dir", "antigravity"]' in src
    assert 'child_env["AGY_ENABLE_HUB"] = "1"' in src
