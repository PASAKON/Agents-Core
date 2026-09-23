"""GH #65 (second half): close_tab must never match a tab by a short task-id prefix.

`task_id[:6]` is "task-" plus ONE character, so it matched other workers' tabs.
The message path moved to the mailbox (2026-08-14); this was the last user.
"""
import inspect

from tools import itermtab


def test_close_tab_has_no_short_prefix_fallback():
    src = inspect.getsource(itermtab.close_tab)
    assert "[:6]" not in src
    assert "fallback" not in src.lower()
