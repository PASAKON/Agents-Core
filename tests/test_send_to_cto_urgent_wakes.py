"""A worker's urgent report wakes its C-level owner; a normal report stays quiet (CEO 18 Nov 2026)."""
from unittest.mock import Mock

import pytest

from tools import send_to_cto as stc


@pytest.mark.parametrize("prio,woke", [("urgent", True), ("normal", False)])
def test_worker_report_to_clevel(monkeypatch, prio, woke):
    monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)
    monkeypatch.setattr(stc.mailbox, "envelope_on", lambda: False)
    monkeypatch.setattr(stc.mailbox, "quiet_for", lambda role, kind: kind in ("report", "fyi"))
    wake = Mock()
    monkeypatch.setattr(stc, "_attempt_wake", wake)
    stc._wake("cto", "fresh", "BROWSER_OPERATOR", prio, "report")
    assert wake.called is woke
