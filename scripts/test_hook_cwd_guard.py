"""Tests for scripts/hook-cwd-guard.py (ADR 0028 §6, session cto-0e8d80b8).

Covers every case named in the task brief — the real commands that left a
CTO session's Bash cwd wrong 5x on 2026-09-22, plus the shapes that must
stay allowed — along with the escape hatch and fail-open behaviour.

Run standalone:   python scripts/test_hook_cwd_guard.py
Or under pytest:  pytest scripts/test_hook_cwd_guard.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK_SRC = ROOT / "scripts" / "hook-cwd-guard.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("hook_cwd_guard_under_test", HOOK_SRC)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


MOD = _load_hook()


def _run(monkeypatch: pytest.MonkeyPatch, command: str, home: str = "/repo") -> tuple[int, str]:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", home)
    monkeypatch.delenv("CWD_GUARD", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": home,
    })))
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    rc = MOD.main()
    return rc, err.getvalue()


# --------------------------------------------------------------------------
# BLOCK — the real commands that bit the CTO session on 2026-09-22
# --------------------------------------------------------------------------

def test_block_two_sequential_cds_ends_elsewhere(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, err = _run(monkeypatch, "cd /a && x; cd /b && y", home="/repo")
    assert rc == 2
    assert "/b" in err


def test_block_for_loop_cd_with_variable_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(monkeypatch, 'for d in /x /y; do cd "$d"; ls; done', home="/repo")
    assert rc == 2


def test_block_leading_cd_counts_heredoc_body_does_not(monkeypatch: pytest.MonkeyPatch) -> None:
    command = (
        "cd /Users/gob/Projects/Agents-Memory && cat > f <<'MD'\n"
        "…cd inside heredoc…\n"
        "MD"
    )
    rc, err = _run(monkeypatch, command, home="/repo")
    assert rc == 2
    assert "Agents-Memory" in err


def test_block_cd_variable_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(monkeypatch, "cd $A && git push", home="/repo")
    assert rc == 2


# --------------------------------------------------------------------------
# ALLOW — shapes that must keep working
# --------------------------------------------------------------------------

def test_allow_subshell_cd_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(monkeypatch, "(cd /a && make)", home="/repo")
    assert rc == 0


def test_allow_command_substitution_cd_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(monkeypatch, "x=$(cd /a && pwd)", home="/repo")
    assert rc == 0


def test_allow_cd_into_home_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(monkeypatch, "cd /home && pytest", home="/home")
    assert rc == 0


def test_allow_cd_out_and_back_to_home(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(monkeypatch, "cd /a && x && cd /home", home="/home")
    assert rc == 0


def test_allow_cd_in_a_quoted_string_is_just_text(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(monkeypatch, 'echo "cd there"', home="/repo")
    assert rc == 0


def test_allow_git_dash_c_is_not_a_cd(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(monkeypatch, "git -C /a status", home="/repo")
    assert rc == 0


def test_allow_python_heredoc_chdir_is_not_shell_cd(monkeypatch: pytest.MonkeyPatch) -> None:
    command = "python3 - <<'PY'\nos.chdir('/x')\nPY"
    rc, _ = _run(monkeypatch, command, home="/repo")
    assert rc == 0


def test_allow_no_cd_at_all(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(monkeypatch, "pytest scripts/ -q", home="/repo")
    assert rc == 0


def test_allow_cd_dash_returns_to_home(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = _run(monkeypatch, "cd /a; cd -", home="/repo")
    assert rc == 0


# --------------------------------------------------------------------------
# escape hatch + fail-open
# --------------------------------------------------------------------------

def test_escape_hatch_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CWD_GUARD", "off")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/repo")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "cd /elsewhere && rm -rf ."},
        "cwd": "/repo",
    })))
    assert MOD.main() == 0


def test_non_json_stdin_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json{{{"))
    assert MOD.main() == 0


def test_no_command_never_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/repo")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "tool_name": "Bash", "tool_input": {}, "cwd": "/repo",
    })))
    assert MOD.main() == 0


def test_missing_home_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "cd /somewhere && ls"},
        "cwd": "",
    })))
    assert MOD.main() == 0


def test_block_message_is_short_and_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, err = _run(monkeypatch, "cd /elsewhere && ls", home="/repo")
    assert rc == 2
    assert "would leave the session in" in err
    assert "home is /repo" in err
    assert "git -C" in err
    assert err.count("\n") <= 5


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
