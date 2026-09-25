"""tools/watch_remote_workers.py -- the pure pane classifier (no ssh)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "watch_remote_workers", Path(__file__).resolve().parent.parent / "tools" / "watch_remote_workers.py")
w = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(w)


def test_gone_when_no_pane():
    assert w.classify(None) == "gone"
    assert w.classify("") == "gone"


def test_teach_prompt_wins_over_the_dialog_line_it_carries():
    pane = "Teach auto mode about your environment?\n 1. Yes\n 3. Don't show again\nEnter to confirm"
    assert w.classify(pane) == "teach-prompt"


def test_other_confirm_dialog_needs_a_human():
    assert w.classify("Allow Bash(rm -rf x)?\nEnter to confirm · Esc to cancel") == "DIALOG"


def test_finish_marker_and_running():
    assert w.classify("pushed branch\n❯ Run %ORG_WORKER_FINISH%") == "finished"
    assert w.classify("✻ Thundering… (1m 10s)") == "running"
