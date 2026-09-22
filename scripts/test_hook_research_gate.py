"""Tests for scripts/hook-research-gate.py (ADR 0028 §6, session cto-0e8d80b8).

Covers: blocks WebSearch/WebFetch while unarmed, arms on wiki_search / a
Read|Grep of a research/ path / a Bash command mentioning research, 12h
expiry, the RESEARCH_GATE=off escape hatch, and fail-open on bad input.

Run standalone:   python scripts/test_hook_research_gate.py
Or under pytest:  pytest scripts/test_hook_research_gate.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK_SRC = ROOT / "scripts" / "hook-research-gate.py"


def _counter():
    n = 0
    while True:
        n += 1
        yield n


_next_id = _counter().__next__


def _load_hook():
    spec = importlib.util.spec_from_file_location(
        f"hook_research_gate_under_test_{_next_id()}", HOOK_SRC
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _feed_stdin(monkeypatch: pytest.MonkeyPatch, event: dict) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("RESEARCH_GATE", raising=False)


def _capture_stderr(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    return buf


# --------------------------------------------------------------------------
# blocks while unarmed
# --------------------------------------------------------------------------

def test_blocks_websearch_when_unarmed(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    err = _capture_stderr(monkeypatch)
    _feed_stdin(monkeypatch, {
        "session_id": "s1", "tool_name": "WebSearch",
        "tool_input": {"query": "anything"},
    })
    assert mod.main() == 2
    assert "research" in err.getvalue().lower()
    assert err.getvalue().count("\n") <= 6


def test_blocks_webfetch_when_unarmed(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    _feed_stdin(monkeypatch, {
        "session_id": "s1", "tool_name": "WebFetch",
        "tool_input": {"url": "https://example.com"},
    })
    assert mod.main() == 2


# --------------------------------------------------------------------------
# arming
# --------------------------------------------------------------------------

def test_arms_on_wiki_search_call(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    _feed_stdin(monkeypatch, {
        "session_id": "s2", "tool_name": "mcp__org__wiki_search",
        "tool_input": {"query": "seedance prompt structure"},
    })
    assert mod.main() == 0
    assert (Path.home() / ".gateguard" / "research-gate-s2.ok").is_file()


def test_arms_on_read_research_path(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    _feed_stdin(monkeypatch, {
        "session_id": "s3", "tool_name": "Read",
        "tool_input": {"file_path": "/Users/gob/MoonieXHQ/Agents/Wikis/research/2026-09-03-x.md"},
    })
    assert mod.main() == 0
    assert (Path.home() / ".gateguard" / "research-gate-s3.ok").is_file()


def test_arms_on_read_research_index(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    _feed_stdin(monkeypatch, {
        "session_id": "s4", "tool_name": "Read",
        "tool_input": {"file_path": "/Users/gob/MoonieXHQ/Agents/Wikis/research/RESEARCH-INDEX.md"},
    })
    assert mod.main() == 0
    assert (Path.home() / ".gateguard" / "research-gate-s4.ok").is_file()


def test_arms_on_grep_research_path(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    _feed_stdin(monkeypatch, {
        "session_id": "s5", "tool_name": "Grep",
        "tool_input": {"pattern": "seedance", "path": "/Users/gob/MoonieXHQ/Agents/Wikis/research/"},
    })
    assert mod.main() == 0
    assert (Path.home() / ".gateguard" / "research-gate-s5.ok").is_file()


def test_arms_on_bash_mentioning_research(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    _feed_stdin(monkeypatch, {
        "session_id": "s6", "tool_name": "Bash",
        "tool_input": {"command": "ls /Users/gob/MoonieXHQ/Agents/Wikis/research/"},
    })
    assert mod.main() == 0
    assert (Path.home() / ".gateguard" / "research-gate-s6.ok").is_file()


def test_unrelated_bash_does_not_arm(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    _feed_stdin(monkeypatch, {
        "session_id": "s7", "tool_name": "Bash",
        "tool_input": {"command": "ls /tmp"},
    })
    assert mod.main() == 0
    assert not (Path.home() / ".gateguard" / "research-gate-s7.ok").exists()


def test_armed_session_allows_websearch(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    _feed_stdin(monkeypatch, {
        "session_id": "s8", "tool_name": "mcp__org__wiki_search",
        "tool_input": {"query": "x"},
    })
    assert mod.main() == 0

    _feed_stdin(monkeypatch, {
        "session_id": "s8", "tool_name": "WebSearch",
        "tool_input": {"query": "anything"},
    })
    assert mod.main() == 0


# --------------------------------------------------------------------------
# expiry
# --------------------------------------------------------------------------

def test_marker_expires_after_12h(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    marker = Path.home() / ".gateguard" / "research-gate-s9.ok"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(time.time() - (12 * 3600 + 60)))

    _feed_stdin(monkeypatch, {
        "session_id": "s9", "tool_name": "WebSearch",
        "tool_input": {"query": "anything"},
    })
    assert mod.main() == 2


def test_marker_within_12h_still_allows(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    marker = Path.home() / ".gateguard" / "research-gate-s10.ok"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(time.time() - 3600))

    _feed_stdin(monkeypatch, {
        "session_id": "s10", "tool_name": "WebSearch",
        "tool_input": {"query": "anything"},
    })
    assert mod.main() == 0


# --------------------------------------------------------------------------
# escape hatch + fail-open
# --------------------------------------------------------------------------

def test_escape_hatch_off(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    monkeypatch.setenv("RESEARCH_GATE", "off")
    _feed_stdin(monkeypatch, {
        "session_id": "s11", "tool_name": "WebSearch",
        "tool_input": {"query": "anything"},
    })
    assert mod.main() == 0


def test_non_json_stdin_never_raises_and_does_not_block(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json{{{"))
    assert mod.main() == 0


def test_missing_fields_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    _feed_stdin(monkeypatch, {})
    assert mod.main() == 0


def test_passthrough_unrelated_tool_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_hook()
    err = _capture_stderr(monkeypatch)
    _feed_stdin(monkeypatch, {
        "session_id": "s12", "tool_name": "Edit",
        "tool_input": {"file_path": "/tmp/x.py"},
    })
    assert mod.main() == 0
    assert err.getvalue() == ""


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
