"""gc letters the owner when it cancels a task it never ran (COO 2026-11-26)."""
from __future__ import annotations

import sys
import types

from tools import gc_stale_tasks as gc


def _capture(monkeypatch):
    sent = []
    fake = types.ModuleType("lib.mailbox")
    fake.send = lambda *a, **k: sent.append((a, k))
    monkeypatch.setitem(sys.modules, "lib.mailbox", fake)
    import lib
    monkeypatch.setattr(lib, "mailbox", fake, raising=False)
    return sent


def test_letter_carries_last_delegate_log_line(monkeypatch):
    sent = _capture(monkeypatch)
    t = {"id": "task-x", "title": "S1 test fix", "owner_cto": "dfb41593",
         "owner_role": "project_head",
         "delegate_log": "host: contabo\nIRON §59 rule 7: runner pinned by hand"}
    gc._tell_owner(t, "pending >30 min, never delegated")
    assert len(sent) == 1
    args, kw = sent[0]
    assert args[0] == "project_head" and args[1] == "dfb41593"
    assert "task-x" in args[2] and "rule 7" in args[2]
    assert kw["kind"] == "blocker"


def test_no_owner_no_letter(monkeypatch):
    sent = _capture(monkeypatch)
    gc._tell_owner({"id": "task-y", "owner_cto": None}, "x")
    assert sent == []


def test_mailbox_failure_never_raises(monkeypatch):
    fake = types.ModuleType("lib.mailbox")

    def boom(*a, **k):
        raise OSError("disk full")
    fake.send = boom
    monkeypatch.setitem(sys.modules, "lib.mailbox", fake)
    import lib
    monkeypatch.setattr(lib, "mailbox", fake, raising=False)
    gc._tell_owner({"id": "task-z", "owner_cto": "cto1"}, "x")
