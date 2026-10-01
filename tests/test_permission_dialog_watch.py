"""GH #182 part 3: scripts/permission_dialog_watch.py."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "permission_dialog_watch", ROOT / "scripts" / "permission_dialog_watch.py")
pdw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pdw)

BASH_DIALOG = (
    "Bash command\n  cat >> ~/.ssh/authorized_keys\n"
    "Do you want to proceed?\n ❯ 1. Yes\n   2. No, and tell Claude what to do differently\n"
)
TRUST_DIALOG = "Quick safety check\n ❯ No, exit\n   Yes, I trust this folder\n"


def test_dialog_text_recognises_claude_dialogs():
    assert pdw.dialog_text(BASH_DIALOG) == "Do you want to proceed?"
    assert "folder-trust" in pdw.dialog_text(TRUST_DIALOG)
    assert pdw.dialog_text("> Do you want to proceed with the plan? I think yes.\n") is None
    assert pdw.dialog_text("working...\n") is None


def _run(tmp_path, now, screens, sent):
    return pdw.run_once(
        after_s=300, state_path=tmp_path / "state.json", now=now,
        sessions=lambda: list(screens), screen=lambda s: screens[s],
        send=lambda body: sent.append(body))


def test_alerts_once_after_five_minutes_then_rearms_when_cleared(tmp_path):
    sent: list[str] = []
    screens = {"cto-4bb20df8": BASH_DIALOG, "cmo-11111111": "idle\n"}

    assert _run(tmp_path, 1000, screens, sent) == []        # first seen
    assert _run(tmp_path, 1200, screens, sent) == []        # 200 s: not yet
    assert _run(tmp_path, 1301, screens, sent) == ["cto-4bb20df8"]
    assert len(sent) == 1 and "cto-4bb20df8" in sent[0] and "5 min" in sent[0]
    assert _run(tmp_path, 1900, screens, sent) == []        # no repeat
    assert len(sent) == 1

    screens["cto-4bb20df8"] = "answered\n"
    _run(tmp_path, 2000, screens, sent)
    assert json.loads((tmp_path / "state.json").read_text()) == {}

    screens["cto-4bb20df8"] = BASH_DIALOG                   # a new dialog
    _run(tmp_path, 2100, screens, sent)
    assert _run(tmp_path, 2401, screens, sent) == ["cto-4bb20df8"]
    assert len(sent) == 2


def test_dry_run_writes_nothing(tmp_path, capsys):
    sent: list[str] = []
    state = tmp_path / "state.json"
    pdw.run_once(after_s=0, state_path=state, dry_run=True, now=1,
                 sessions=lambda: ["cto-1"], screen=lambda s: BASH_DIALOG,
                 send=lambda b: sent.append(b))
    assert sent == [] and not state.exists()
    assert "would alert" in capsys.readouterr().out


def test_notify_lands_in_sompong_box(tmp_path):
    path = pdw.notify("hello", root=tmp_path)
    assert path.parent == tmp_path / "secretary-sompong"
    letter = json.loads(path.read_text())
    assert letter["body"] == "hello"
    assert letter["from"] == {"role": "watchdog", "session_id": "permission-dialog"}
