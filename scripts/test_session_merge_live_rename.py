"""Tests for scripts/session_merge.py's rename_live_source() (task-bbdfa8d1).

/session-merge's live-guard (session_list.live_ids()) only refuses when
session A has an OPEN ITERM TAB — it never checks tmux directly. That means
a session whose tab was closed (or force-quit) while its tmux+claude
process kept running slips past that guard undetected. rename_live_source()
is the fix on the naming side: if A's tmux session ("<role>-<a_id>") is
still alive, best-effort stamp its live Claude Remote-Control display name
with "⛔ MERGED→#<b_id>" before anything else touches it — the one window
where that name can still be changed at all (renaming requires a live pane).

Covers:
  1. A's tmux session alive -> sends /rename with the exact ⛔ MERGED→#B text.
  2. A's tmux session NOT alive (the common case -- A already ended cleanly)
     -> no-op, attempted=False, no exception.
  3. dry-run mode never sends, regardless of liveness.
  4. a tmux/send failure is caught and reported, never raised (stamping
     must never block the merge it belongs to).

tools.tmux_session.has_session / send_keys are monkeypatched directly (same
style as scripts/test_cxo_crosstalk.py's sc.tmux_session.has_session /
_wake_tmux_send stubs) -- no real tmux binary, no real subprocess.

Run via:   pytest scripts/test_session_merge_live_rename.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import session_merge  # noqa: E402 -- scripts/ is on sys.path via pytest's prepend import mode
from tools import tmux_session  # noqa: E402


def test_sends_rename_when_source_tmux_alive(monkeypatch):
    calls = []
    monkeypatch.setattr(tmux_session, "has_session", lambda name: name == "cto-aaaa1111")
    monkeypatch.setattr(tmux_session, "send_keys",
                         lambda name, text, **kw: calls.append((name, text)))

    result = session_merge.rename_live_source("cto", "aaaa1111", "bbbb2222", apply_write=True)

    assert result["attempted"] is True
    assert result["sent"] == "⛔ MERGED→#bbbb2222"
    assert calls == [("cto-aaaa1111", "/rename ⛔ MERGED→#bbbb2222")]


def test_noop_when_source_tmux_not_alive(monkeypatch):
    calls = []
    monkeypatch.setattr(tmux_session, "has_session", lambda name: False)
    monkeypatch.setattr(tmux_session, "send_keys",
                         lambda name, text, **kw: calls.append((name, text)))

    result = session_merge.rename_live_source("cto", "deadbeef", "bbbb2222", apply_write=True)

    assert result["attempted"] is False
    assert "not live" in result["reason"]
    assert calls == []


def test_dry_run_never_sends_even_if_alive(monkeypatch):
    calls = []
    monkeypatch.setattr(tmux_session, "has_session", lambda name: True)
    monkeypatch.setattr(tmux_session, "send_keys",
                         lambda name, text, **kw: calls.append((name, text)))

    result = session_merge.rename_live_source("cto", "aaaa1111", "bbbb2222", apply_write=False)

    assert result["attempted"] is False
    assert result["reason"] == "dry-run"
    assert calls == []


def test_send_failure_is_caught_not_raised(monkeypatch):
    monkeypatch.setattr(tmux_session, "has_session", lambda name: True)

    def _boom(name, text, **kw):
        raise RuntimeError("tmux exploded")
    monkeypatch.setattr(tmux_session, "send_keys", _boom)

    result = session_merge.rename_live_source("cto", "aaaa1111", "bbbb2222", apply_write=True)

    assert result["attempted"] is True
    assert result["sent"] is None
    assert "tmux exploded" in result["error"]


def test_targets_the_exact_source_session_name(monkeypatch):
    """Never rename a session that is not ours -- must address A
    ("<role>-<a_id>"), never B (the session running the merge)."""
    seen_names = []
    monkeypatch.setattr(tmux_session, "has_session", lambda name: seen_names.append(name) or True)
    monkeypatch.setattr(tmux_session, "send_keys", lambda name, text, **kw: None)

    session_merge.rename_live_source("cmo", "source01", "target02", apply_write=True)

    assert seen_names == ["cmo-source01"]
