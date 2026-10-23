"""Quiet-letter sender notices and urgent cross-host mail, without live services."""
import json
from unittest.mock import Mock

import pytest

import lib.mailbox as mailbox
from tools import clevel_gate
from tools import node_dispatch as nd
from tools import send_to_cxo as sc


pytestmark = pytest.mark.usefixtures("ceo_command")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    for var in ("ORG_MAIL_ENVELOPE", "ORG_WAKE_DEBOUNCE_S", "ORG_MESH_DISPATCH"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    locks = tmp_path / "locks"
    locks.mkdir()
    (locks / "cfo-active").write_text("f1")
    monkeypatch.setattr(sc, "LOCKS_DIR", locks)
    monkeypatch.setattr(sc, "_log_hop", Mock())
    monkeypatch.setattr(sc, "_attempt_wake", Mock(return_value=True))
    monkeypatch.setattr(sc, "attempt_wake", Mock(return_value=True))
    monkeypatch.setattr(nd, "_clevel_session_live", lambda role, sid: True)
    monkeypatch.setattr(nd, "_is_windows", lambda: False)


@pytest.mark.parametrize("envelope", [False, True])
@pytest.mark.parametrize("route", ["local", "delivered", "queued"])
@pytest.mark.parametrize("kind,body,quiet_kind", [
    ("report", "farm stopped", "report"),
    (None, "fyi · x", "fyi"),
    ("blocker", "farm stopped", None),
])
def test_clevel_quiet_notice(monkeypatch, envelope, route, kind, body, quiet_kind):
    if envelope:
        monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    if route != "local":
        monkeypatch.setattr(sc, "_active_session_id", lambda role: None)
        monkeypatch.setattr(sc, "_remote_target", lambda role: ("elsewhere", "f1"))
        monkeypatch.setattr(sc, "self_host", lambda: "here")
        monkeypatch.setattr(sc.db, "create_letter", Mock(return_value=42))
        monkeypatch.setattr(sc, "dispatch_letter", lambda lid: route)

    out = sc.send("cfo", body, kind=kind)

    prefix = {"local": "queued to CFO #f1", "delivered": "delivered to CFO #f1 on elsewhere",
              "queued": "queued for elsewhere"}[route]
    assert out.startswith(prefix)
    if quiet_kind:
        assert out.splitlines()[-1] == (
            f"note: a {quiet_kind} letter never wakes {sc.display_for('cfo')}; "
            "it waits for the CEO's next prompt. If it must be acted on now, "
            "send it again as kind blocker (body starting `blocker · `)."
        )
        sc._attempt_wake.assert_not_called()
    else:
        assert "\nnote:" not in out
    if route == "local":
        [path] = (mailbox.INBOX_ROOT / "cfo-f1").glob("*.json")
        assert json.loads(path.read_text())["body"] == body
    else:
        assert sc.db.create_letter.call_args.args == ("elsewhere", "cfo", body)


@pytest.mark.parametrize("envelope", [False, True])
def test_project_head_report_has_no_notice(monkeypatch, envelope):
    if envelope:
        monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    monkeypatch.setattr(clevel_gate, "live_lock", lambda *a, **kw: 4242)
    out = sc.send("project_head-0a1b2c3d", "status", subject="status", kind="report")
    assert out.startswith("queued to Project Head #0a1b2c3d")
    assert "\nnote:" not in out


@pytest.mark.parametrize("kind,prio,woke", [
    ("blocker", "urgent", True),
    ("ask", "urgent", True),
    ("report", "normal", False),
])
def test_cross_host_letter_priority(monkeypatch, kind, prio, woke):
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    mailbox.note_sweep(root=mailbox.INBOX_ROOT)
    wake_due = Mock(wraps=mailbox.wake_due)
    monkeypatch.setattr(mailbox, "wake_due", wake_due)
    body = f"{kind} · farm stopped"
    out = nd._write_clevel_letter({"to_session": "s1", "body": body,
                                   "from_role": "project_head", "from_session": "0a1b2c3d",
                                   "from_host": "elsewhere"}, "cto")
    [path] = (mailbox.INBOX_ROOT / "cto-s1").glob("*.json")
    letter = json.loads(path.read_text())
    assert (letter["kind"], letter["prio"], letter["body"]) == ("message", prio, body)
    wake_due.assert_called_once_with("cto", "s1", prio, kind=kind)
    assert out["woke"] is woke
    assert sc.attempt_wake.call_count == int(woke)
