"""tools/mail_wake.py -- wake the session that waits on a mailbox letter.

The Console drops a Run Inbox result letter into state/inbox/<box>/ when a card
ends and calls `python -m tools.mail_wake <box>` so an idle session reads it now
instead of with the CEO's next prompt. Every test builds its own inbox under
tmp_path and every wake is a recorder: no tmux, hub or network is reached.

Run: .venv/bin/python -m pytest tests/test_mail_wake.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import lib.mailbox as mailbox  # noqa: E402
import tools.agent_transport as agent_transport  # noqa: E402
import tools.mail_wake as mail_wake  # noqa: E402
import tools.send_to_cxo as send_to_cxo  # noqa: E402
import tools.tmux_session as tmux_session  # noqa: E402
from lib.roles import c_level_roles  # noqa: E402


@pytest.fixture
def inbox(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "inbox"
    root.mkdir()
    monkeypatch.setattr(mailbox, "INBOX_ROOT", root)
    monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)
    return root


@pytest.fixture
def wakes(monkeypatch) -> list[tuple]:
    """Both wake functions replaced by one recorder; each call lands here."""
    calls: list[tuple] = []

    def cxo(role, sid, label):
        calls.append(("cxo", role, sid, label))
        return True

    def worker(session, label, log_prefix, **kw):
        calls.append(("worker", session, label, log_prefix))
        return True

    monkeypatch.setattr(send_to_cxo, "attempt_wake", cxo)
    monkeypatch.setattr(agent_transport, "attempt_wake", worker)
    return calls


def _letter(inbox: Path, box: str) -> Path:
    """One unread result letter in `box`, written the way the hub writes it."""
    role, _, sid = box.partition("-")
    return mailbox.send(role, sid, "RUN-20261030-0412-abcd done", "run-inbox", "hub", root=inbox)


# ------------------------------------------------------------- box name rules
@pytest.mark.parametrize("name", [
    "", ".", "..", ".hidden", "-cto-x", "a/b", "../cto-x", "cto x", "cto-x\n", "cto-é", "x" * 129,
])
def test_a_name_that_is_not_one_path_segment_is_refused(inbox, wakes, name):
    assert mail_wake.wake(name) == {"box": name, "woke": False, "reason": "invalid box name"}
    assert wakes == []


def test_a_name_of_the_longest_legal_length_is_checked_not_refused(inbox, wakes):
    out = mail_wake.wake("x" * 128)
    assert out["reason"] == "no unread letter"


# ------------------------------------------------------- no unread letter, no wake
def test_a_box_that_does_not_exist_is_not_woken(inbox, wakes):
    assert mail_wake.wake("cto-fresh") == {"box": "cto-fresh", "woke": False, "reason": "no unread letter"}
    assert wakes == []


def test_an_empty_box_is_not_woken(inbox, wakes):
    (inbox / "cto-fresh").mkdir()
    assert mail_wake.wake("cto-fresh")["reason"] == "no unread letter"
    assert wakes == []


def test_letters_already_read_do_not_wake(inbox, wakes):
    box = inbox / "cto-fresh"
    (box / "read").mkdir(parents=True)
    (box / "read" / "20261030T000000000000Z-run-inbox-hub.json").write_text('{"body": "old"}')
    (box / ".last_wake").write_text("1.0")
    (box / "note.txt").write_text("not a letter")
    (box / "broken.json").write_text("{not json")
    assert mail_wake.wake("cto-fresh")["reason"] == "no unread letter"
    assert wakes == []


# --------------------------------------------------------------- who is woken
def test_a_project_head_box_gets_the_cxo_wake_at_once(inbox, wakes):
    _letter(inbox, "project_head-b2ff34d1")
    out = mail_wake.wake("project_head-b2ff34d1")
    assert out == {"box": "project_head-b2ff34d1", "woke": True, "reason": "woke"}
    assert wakes == [("cxo", "project_head", "b2ff34d1", "RUN-INBOX")]


@pytest.mark.parametrize("role", c_level_roles())
def test_every_c_level_box_gets_the_cxo_wake(inbox, wakes, role):
    box = f"{role}-e785343f"
    _letter(inbox, box)
    assert mail_wake.wake(box)["woke"] is True
    assert wakes == [("cxo", role, "e785343f", "RUN-INBOX")]


def test_a_session_id_that_is_not_hex_is_still_a_c_level_box(inbox, wakes):
    _letter(inbox, "cto-fresh")
    assert mail_wake.wake("cto-fresh", "ASK-CEO")["woke"] is True
    assert wakes == [("cxo", "cto", "fresh", "ASK-CEO")]


def test_a_worker_box_gets_its_tmux_session_woken(inbox, wakes):
    _letter(inbox, "dev-task-8669cf28")
    out = mail_wake.wake("dev-task-8669cf28")
    assert out == {"box": "dev-task-8669cf28", "woke": True, "reason": "woke"}
    assert wakes == [("worker", "wd-8669cf28", "RUN-INBOX", "mail_wake")]


def test_a_worker_with_no_live_tmux_session_reports_not_woken(inbox, monkeypatch):
    asked = []
    monkeypatch.setattr(tmux_session, "has_session", lambda s: asked.append(s) or False)
    _letter(inbox, "developer-task-8669cf28")
    out = mail_wake.wake("developer-task-8669cf28")
    assert out == {"box": "developer-task-8669cf28", "woke": False, "reason": "no live session reached"}
    assert asked == ["wd-8669cf28"]


@pytest.mark.parametrize("box", ["ceo-abc12345", "run-inbox-hub", "cto", "dev-task-12", "dev-task-8669CF28",
                                 "dev-8669cf28", "task-8669cf28"])
def test_any_other_box_gets_no_wake(inbox, wakes, box):
    (inbox / box).mkdir()
    (inbox / box / "x.json").write_text(json.dumps({"body": "hi", "from": {}}))
    out = mail_wake.wake(box)
    assert out["woke"] is False and out["reason"] == "not a session box"
    assert wakes == []


# ----------------------------------------------------------------- symlinks
def test_a_symlinked_box_is_refused_and_left_alone(tmp_path, inbox, wakes):
    real = tmp_path / "elsewhere"
    real.mkdir()
    letter = real / "20261030T000000000000Z-a-b.json"
    letter.write_text(json.dumps({"body": "x", "from": {}}))
    (inbox / "cto-evil").symlink_to(real, target_is_directory=True)
    out = mail_wake.wake("cto-evil")
    assert out == {"box": "cto-evil", "woke": False, "reason": "box is a symlink, refused"}
    assert wakes == [] and letter.exists()


def test_a_symlinked_letter_is_not_an_unread_letter(tmp_path, inbox, wakes):
    secret = tmp_path / "outside.json"
    secret.write_text(json.dumps({"body": "x", "from": {}}))
    box = inbox / "cto-fresh"
    box.mkdir()
    (box / "20261030T000000000000Z-a-b.json").symlink_to(secret)
    assert mail_wake.wake("cto-fresh")["reason"] == "no unread letter"
    assert wakes == []


# ------------------------------------------------- best effort, no hub, CLI
def test_a_wake_that_raises_is_reported_not_raised(inbox, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("tmux exploded")

    monkeypatch.setattr(send_to_cxo, "attempt_wake", boom)
    _letter(inbox, "cto-fresh")
    assert mail_wake.wake("cto-fresh") == {"box": "cto-fresh", "woke": False, "reason": "error: RuntimeError"}


def test_a_wake_that_reaches_nothing_says_so(inbox, monkeypatch):
    monkeypatch.setattr(send_to_cxo, "attempt_wake", lambda *a: False)
    _letter(inbox, "cto-fresh")
    assert mail_wake.wake("cto-fresh") == {"box": "cto-fresh", "woke": False, "reason": "no live session reached"}


def test_c_level_and_ph_boxes_never_touch_the_hub(inbox, wakes, monkeypatch):
    monkeypatch.delenv("ORG_DB_URL", raising=False)

    def hub(*a, **k):
        raise AssertionError("mail_wake reached the task ledger")

    for name in ("get_conn", "get_task", "init"):
        monkeypatch.setattr(db_mod, name, hub)
    for box in ("project_head-b2ff34d1", "cto-fresh"):
        _letter(inbox, box)
        assert mail_wake.wake(box)["woke"] is True


def test_main_prints_one_json_line_and_exits_0_when_nothing_is_woken(inbox, wakes, capsys):
    assert mail_wake.main(["cto-fresh"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"box": "cto-fresh", "woke": False, "reason": "no unread letter"}


def test_main_passes_the_label_through(inbox, wakes, capsys):
    _letter(inbox, "cmo-e785343f")
    assert mail_wake.main(["cmo-e785343f", "--label", "Q-ANSWER"]) == 0
    assert json.loads(capsys.readouterr().out)["woke"] is True
    assert wakes == [("cxo", "cmo", "e785343f", "Q-ANSWER")]


def test_main_exits_2_on_a_usage_error(inbox, wakes, capsys):
    assert mail_wake.main(["../cto-x"]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "invalid box name"
    with pytest.raises(SystemExit) as e:
        mail_wake.main([])
    assert e.value.code == 2


def test_cli_runs_as_a_plain_process_without_the_hub(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "ORG_DB_URL"}
    env["ORG_ROOT"] = str(tmp_path)   # an inbox of its own: nothing real is read or woken
    run = lambda *argv: subprocess.run(  # noqa: E731
        [sys.executable, "-m", "tools.mail_wake", *argv], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=60)
    ok = run("project_head-b2ff34d1")
    assert ok.returncode == 0, ok.stderr
    assert json.loads(ok.stdout) == {"box": "project_head-b2ff34d1", "woke": False, "reason": "no unread letter"}
    bad = run("../x")
    assert bad.returncode == 2 and json.loads(bad.stdout)["reason"] == "invalid box name"
