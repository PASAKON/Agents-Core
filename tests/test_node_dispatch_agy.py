"""Tests for node_dispatch `agy_list` verb and `_write_agy_letter` branch of `deliver_letter` (task-4983a577)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lib import config as config_mod
from lib import db as db_mod
from lib import mailbox, mesh
from tools import agy_card_run, mail_wake, send_to_agy
from tools import node_dispatch as nd

UUID_MAC_APP = "a753ef73-6f10-4c9c-a2c0-8b0e2088a111"
UUID_OTHER = "deadbeef-1111-2222-3333-444455556666"


@pytest.fixture(autouse=True)
def _isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    for var in (
        "ORG_DB_URL",
        "CTO_SESSION_ID",
        "CXO_SESSION_ID",
        "CXO_ROLE",
        "SSH_ORIGINAL_COMMAND",
        "SSH_CLIENT",
    ):
        monkeypatch.delenv(var, raising=False)
    db_mod.init()
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(config_mod, "self_host", lambda: "mac")
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    monkeypatch.setattr(mail_wake, "AGY_SESSIONS_DIR", tmp_path / "agy-sessions")
    monkeypatch.setattr(agy_card_run, "AGY_SESSIONS_DIR", tmp_path / "agy-sessions")
    monkeypatch.setattr(nd, "MAINTENANCE_AUDIT_DIR", tmp_path / "audit")


@pytest.mark.parametrize(
    "raw",
    [
        "agy_list extra",
        "agy_list --limit 10",
        "agy_list --json",
        "agy_list mac",
        "agy_list 1 2",
        "agy_list ; id",
        "agy_list $(id)",
        "AGY_LIST",
    ],
)
def test_agy_list_rejects_extra_args_and_malformed_calls(
    raw: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[Any] = []
    monkeypatch.setattr(send_to_agy, "scan_local_host", lambda *a, **kw: called.append((a, kw)) or [])

    out, code = nd.run_command(raw)
    assert code == 2, (raw, out)
    assert out["ok"] is False
    assert called == []


def test_agy_list_dispatch_and_mesh_build_argv_reject_extra_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[Any] = []
    monkeypatch.setattr(send_to_agy, "scan_local_host", lambda *a, **kw: called.append((a, kw)) or [])

    res = nd.dispatch("agy_list", ["extra"])
    assert res["ok"] is False
    assert "agy_list takes 0 argument(s), got 1" in res["error"]
    assert called == []

    with pytest.raises(nd.Refusal):
        mesh.build_argv("contabo", "agy_list", ("extra",))

    argv = mesh.build_argv("contabo", "agy_list", ())
    assert argv[-1] == "agy_list"


def test_verb_agy_list_returns_only_allowed_fields_and_redacts_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_scan = [
        {
            "kind": "agy",
            "box": f"cto-agy-{UUID_MAC_APP[:8]}",
            "host": "mac",
            "conversation_id": UUID_MAC_APP,
            "uuid": UUID_MAC_APP,
            "role": "cto",
            "session_id": f"agy-{UUID_MAC_APP[:8]}",
            "cwd": "/Users/gob/MoonieXHQ/Agents/Core",
            "last_activity": "2026-11-18T21:00:00Z",
            "title": "Fix token sk-secret12345678901234567890\nand check https://user:pass@example.com/repo " + ("x" * 100),
            "surface": "App",
            "app_vs_cli": "App",
            "model": "gemini-4-argon-high",
            "mode": "accept-edits",
            "csrf_token": "super-secret-csrf",
            "ls_address": "127.0.0.1:42424",
            "agentapi_exe": "/Applications/Antigravity.app/Contents/MacOS/agentapi",
            "app_data_dir": "/Users/gob/.gemini/antigravity",
        }
    ]
    seen_calls: list[tuple[str, int]] = []

    def fake_scan(host: str, *, limit: int = 50, **kw: Any) -> list[dict[str, Any]]:
        seen_calls.append((host, limit))
        return raw_scan

    monkeypatch.setattr(send_to_agy, "scan_local_host", fake_scan)

    out, code = nd.run_command("agy_list")
    assert code == 0 and out["ok"] is True
    assert seen_calls == [("mac", nd.AGY_LIST_LIMIT)]

    result = out["result"]
    assert result["host"] == "mac"
    assert len(result["conversations"]) == 1
    row = result["conversations"][0]
    assert set(row.keys()) == {"box", "uuid", "cwd", "last_activity", "title", "surface"}
    assert row["box"] == f"cto-agy-{UUID_MAC_APP[:8]}"
    assert row["uuid"] == UUID_MAC_APP
    assert row["cwd"] == "/Users/gob/MoonieXHQ/Agents/Core"
    assert row["last_activity"] == "2026-11-18T21:00:00Z"
    assert row["surface"] == "App"
    assert "\n" not in row["title"]
    assert len(row["title"]) <= nd.AGY_TITLE_CHARS
    assert "sk-secret" not in row["title"]
    assert "user:pass" not in row["title"]
    assert "super-secret-csrf" not in json.dumps(out)
    assert "42424" not in json.dumps(out)


def test_w27_grammar_requires_agy_list_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Demonstrate why tests/test_w27_security.py fails without `agy_list` in `_GRAMMAR`
    and passes once `\"agy_list\": ()` is added."""
    monkeypatch.setattr(nd, "HANDLERS", {v: (lambda *a, v=v: {"stub": v}) for v in nd.HANDLERS})
    out, code = nd.run_command("agy_list")
    assert (code, out["ok"]) == (0, True)

    old_grammar = {"probe", "kit", "pid_alive", "spawn_worker", "kill_worker", "publish_branch", "deliver_letter"}
    assert "agy_list" not in old_grammar
    updated_grammar = {**{k: () for k in old_grammar}, "agy_list": ()}
    assert "agy_list" in updated_grammar and nd._ARGSPEC["agy_list"] == ()


def _make_agy_letter(
    *,
    to_host: str = "mac",
    to_role: str = "cto",
    to_session: str | None = f"agy-{UUID_MAC_APP[:8]}",
    from_role: str = "cto",
    from_session: str = "fresh",
    from_host: str = "contabo",
    body: str = "Please inspect Mac layout",
) -> int:
    return db_mod.create_letter(
        to_host,
        to_role,
        body,
        to_session=to_session,
        from_role=from_role,
        from_session=from_session,
        from_host=from_host,
    )


def test_write_agy_letter_delivers_and_wakes_registered_unparked_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions_dir = tmp_path / "agy-sessions"
    box = f"cto-agy-{UUID_MAC_APP[:8]}"
    agy_card_run.register_session(
        box=box,
        role="cto",
        conversation_id=UUID_MAC_APP,
        cwd="/Users/gob/MoonieXHQ/Agents/Core",
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "mac"},
    )

    wake_calls: list[tuple[str, str]] = []

    def fake_wake(target_box: str, label: str = "RUN-INBOX") -> dict[str, Any]:
        wake_calls.append((target_box, label))
        return {"box": target_box, "woke": True, "reason": mail_wake.AGY_REASON}

    monkeypatch.setattr(mail_wake, "wake", fake_wake)

    lid = _make_agy_letter()
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 0, out
    assert out["ok"] is True
    assert out["result"] == {
        "letter_id": lid,
        "delivered": True,
        "to": box,
        "woke": True,
    }
    assert wake_calls == [(box, "CTO")]

    queued = mailbox.peek("cto", f"agy-{UUID_MAC_APP[:8]}")
    assert len(queued) == 1
    assert queued[0]["body"] == "Please inspect Mac layout"
    assert queued[0]["from"] == {"role": "cto", "session_id": "fresh"}
    assert db_mod.get_letter(lid)["status"] == "delivered"


def test_write_agy_letter_reports_woke_false_and_redacts_why_when_wake_does_not_wake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions_dir = tmp_path / "agy-sessions"
    box = f"cto-agy-{UUID_MAC_APP[:8]}"
    agy_card_run.register_session(
        box=box,
        role="cto",
        conversation_id=UUID_MAC_APP,
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "mac"},
    )
    monkeypatch.setattr(
        mail_wake,
        "wake",
        lambda target_box, label="RUN-INBOX": {
            "box": target_box,
            "woke": False,
            "reason": "runner failed with token sk-secret12345678901234567890",
        },
    )

    lid = _make_agy_letter()
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 0, out
    assert out["ok"] is True
    assert out["result"]["delivered"] is True
    assert out["result"]["woke"] is False
    assert "sk-secret" not in out["result"]["why"]
    assert "***" in out["result"]["why"]
    assert db_mod.get_letter(lid)["status"] == "delivered"


def test_write_agy_letter_refuses_unregistered_session_before_writing_inbox(
    tmp_path: Path,
) -> None:
    lid = _make_agy_letter()
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 1
    assert out["ok"] is False
    assert f"no registered, unparked AGY session cto-agy-{UUID_MAC_APP[:8]} on this host" in out["error"]
    assert mailbox.peek("cto", f"agy-{UUID_MAC_APP[:8]}") == []
    row = db_mod.get_letter(lid)
    assert row["status"] == "pending" and row["attempts"] == 1


def test_write_agy_letter_refuses_parked_session(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "agy-sessions"
    box = f"cto-agy-{UUID_MAC_APP[:8]}"
    rec = agy_card_run.register_session(
        box=box,
        role="cto",
        conversation_id=UUID_MAC_APP,
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "mac"},
    )
    rec["parked"] = True
    (sessions_dir / f"{box}.json").write_text(json.dumps(rec), encoding="utf-8")

    lid = _make_agy_letter()
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 1
    assert out["ok"] is False
    assert f"no registered, unparked AGY session {box} on this host" in out["error"]
    assert mailbox.peek("cto", f"agy-{UUID_MAC_APP[:8]}") == []


def test_write_agy_letter_refuses_mismatched_conversation_uuid(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "agy-sessions"
    box = f"cto-agy-{UUID_MAC_APP[:8]}"
    rec = agy_card_run.register_session(
        box=box,
        role="cto",
        conversation_id=UUID_MAC_APP,
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "mac"},
    )
    rec["conversation_id"] = UUID_OTHER
    (sessions_dir / f"{box}.json").write_text(json.dumps(rec), encoding="utf-8")

    lid = _make_agy_letter()
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 1
    assert out["ok"] is False
    assert "names a conversation that does not match the box" in out["error"]
    assert mailbox.peek("cto", f"agy-{UUID_MAC_APP[:8]}") == []


def test_write_agy_letter_refuses_on_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions_dir = tmp_path / "agy-sessions"
    box = f"cto-agy-{UUID_MAC_APP[:8]}"
    agy_card_run.register_session(
        box=box,
        role="cto",
        conversation_id=UUID_MAC_APP,
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "mac"},
    )
    monkeypatch.setattr(nd, "_is_windows", lambda: True)

    lid = _make_agy_letter()
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 1
    assert out["ok"] is False
    assert "AGY letters are not delivered on Windows hosts" in out["error"]
    assert mailbox.peek("cto", f"agy-{UUID_MAC_APP[:8]}") == []


@pytest.mark.parametrize(
    "bad_kw",
    [
        {"from_role": "../evil"},
        {"from_session": "bad session"},
    ],
)
def test_write_agy_letter_refuses_unsafe_sender_tokens(
    tmp_path: Path,
    bad_kw: dict[str, str],
) -> None:
    sessions_dir = tmp_path / "agy-sessions"
    box = f"cto-agy-{UUID_MAC_APP[:8]}"
    agy_card_run.register_session(
        box=box,
        role="cto",
        conversation_id=UUID_MAC_APP,
        sessions_dir=sessions_dir,
        env={"ORG_HOST": "mac"},
    )

    lid = _make_agy_letter(**bad_kw)
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 1
    assert out["ok"] is False
    assert "unsafe from_" in out["error"]
    assert mailbox.peek("cto", f"agy-{UUID_MAC_APP[:8]}") == []
