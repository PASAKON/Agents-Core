"""Every worker letter wakes its owner, C-level or PH, whatever its kind (CEO 18 Nov 2026)."""
from unittest.mock import Mock

import pytest

from tools import send_to_cto as stc


@pytest.mark.parametrize("owner", ["cto", "cmo", "project_head"])
@pytest.mark.parametrize("prio", ["urgent", "normal"])
@pytest.mark.parametrize("kind", ["report", "fyi", "message"])
def test_worker_letter_always_wakes(monkeypatch, owner, prio, kind):
    monkeypatch.setattr(stc.mailbox, "envelope_on", lambda: True)
    monkeypatch.setattr(stc.mailbox, "note_wake", lambda *a, **k: None)
    monkeypatch.setattr(stc.mailbox, "quiet_for", lambda role, k: k in ("report", "fyi"))
    wake = Mock()
    monkeypatch.setattr(stc, "_attempt_wake", wake)
    stc._wake(owner, "s1", "DEVELOPER", prio, kind)
    assert wake.called
