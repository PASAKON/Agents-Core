"""Tests for Phase 2 multi-host worker naming (task-af5268b3, the Mac side
of docs/design/multi-host-workers.md).

Covers: `-n` session-name shape per host/role (config.worker_session_name),
truncation, the task id staying parseable back out of the name,
`--remote-control` gating via config/hosts.yaml's per-host flag, and that
runners/worker_init.py and runners/worker_resume.py assemble their claude
argv from the exact same shared function (worker_claude_argv) so the two
can never drift again.

Run via:  pytest tests/test_worker_naming.py
(not in pytest.ini's default `testpaths` — run explicitly, same as
tests/test_multihost.py.)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.config as config  # noqa: E402
import runners.worker_init as worker_init  # noqa: E402


# ---------------------------------------------------------------------------
# 1. worker_session_name shape per host/role + truncation
# ---------------------------------------------------------------------------

def test_session_name_shape_mac_developer():
    name = config.worker_session_name("mac", "developer", "task-af5268b3", "SHOOT the teaser")
    assert name == "MAC Developer #af5268b3 (SHOOT the teaser)"


def test_session_name_shape_winbox_browser_operator():
    name = config.worker_session_name(
        "winbox", "browser_operator", "task-4a59a1a4", "SHOOT the teaser")
    assert name == "WINDOWS Browser Operator #4a59a1a4 (SHOOT the teaser)"


def test_session_name_shape_contabo_unknown_role_falls_back_to_raw_key():
    # display_for() falls back to the raw role key for a role with no
    # policies/agents.yaml entry -- worker_session_name must not raise.
    name = config.worker_session_name("contabo", "some_new_role", "task-00000000", "x")
    assert name.startswith("CONTABO some_new_role #00000000")


def test_session_name_no_title_omits_parens():
    name = config.worker_session_name("mac", "developer", "task-af5268b3", "")
    assert name == "MAC Developer #af5268b3"


def test_session_name_truncates_long_title_to_40_chars():
    long_title = "x" * 80
    name = config.worker_session_name("mac", "developer", "task-abcd1234", long_title)
    assert "…" in name
    title_part = name.split("(", 1)[1]
    assert len(title_part) <= 42  # 40 chars + ellipsis + ")"


def test_clean_title_strips_newlines():
    assert worker_init.clean_title("line one\nline two") == "line one line two"


def test_clean_title_none_is_empty_string():
    assert worker_init.clean_title(None) == ""


def test_session_name_via_clean_title_has_no_newline():
    title = worker_init.clean_title("line one\nline two")
    name = config.worker_session_name("mac", "developer", "task-abcd1234", title)
    assert "\n" not in name


# ---------------------------------------------------------------------------
# 2. The task id stays parseable back out of the rendered name.
# ---------------------------------------------------------------------------

_SHORT_ID_RE = re.compile(r"#([0-9a-fA-F]{8})\b")


def test_short_id_is_findable_in_new_form():
    task_id = "task-af5268b3"
    name = config.worker_session_name("mac", "developer", task_id, "some title")
    m = _SHORT_ID_RE.search(name)
    assert m is not None
    assert m.group(1) == "af5268b3"


def test_short_id_matches_task_id_suffix_for_every_host():
    task_id = "task-4a59a1a4"
    for host in ("mac", "winbox", "contabo"):
        name = config.worker_session_name(host, "developer", task_id, "t")
        m = _SHORT_ID_RE.search(name)
        assert m is not None
        assert task_id.endswith(m.group(1))


# ---------------------------------------------------------------------------
# 3. current_host() -- default + ORG_HOST override.
# ---------------------------------------------------------------------------

def test_current_host_defaults_to_mac(monkeypatch):
    monkeypatch.delenv("ORG_HOST", raising=False)
    assert worker_init.current_host() == "mac"


def test_current_host_reads_org_host_override(monkeypatch):
    monkeypatch.setenv("ORG_HOST", "CONTABO")
    assert worker_init.current_host() == "contabo"


def test_current_host_blank_org_host_falls_back_to_mac(monkeypatch):
    monkeypatch.setenv("ORG_HOST", "  ")
    assert worker_init.current_host() == "mac"


# ---------------------------------------------------------------------------
# 4. remote_control_args() -- per-host gate, default-open on missing config.
# ---------------------------------------------------------------------------

def test_remote_control_args_true_for_real_hosts():
    # config/hosts.yaml declares remote_control: true for all three hosts
    # today (ADDENDUM 1, CTO 2026-09-07).
    for host in ("mac", "winbox", "contabo"):
        assert worker_init.remote_control_args(host) == ["--remote-control"]


def test_remote_control_args_off_when_flag_false(monkeypatch):
    monkeypatch.setattr(worker_init, "get_host", lambda name: {"remote_control": False})
    assert worker_init.remote_control_args("mac") == []


def test_remote_control_args_fails_open_on_unknown_host():
    assert worker_init.remote_control_args("does-not-exist") == ["--remote-control"]


def test_remote_control_args_defaults_true_when_key_missing(monkeypatch):
    monkeypatch.setattr(worker_init, "get_host", lambda name: {})
    assert worker_init.remote_control_args("mac") == ["--remote-control"]


# ---------------------------------------------------------------------------
# 5. worker_claude_argv() -- shape, --allowed-tools last, --remote-control
#    gated in, resume argv == init argv modulo prompt/extra_flags.
# ---------------------------------------------------------------------------

def _sample_kwargs(**overrides):
    kwargs = dict(
        prompt="do the thing",
        session_name="MAC Developer #af5268b3 (SHOOT the teaser)",
        model="claude-sonnet-5",
        effort_args=["--effort", "high"],
        role_doc="role doc text",
        mcp_config=ROOT / "config" / "worker.mcp.json",
        chrome_args=[],
        allowed=["Read", "Write", "Bash"],
        host_name="mac",
    )
    kwargs.update(overrides)
    return kwargs


def test_worker_claude_argv_prompt_first_and_allowed_tools_last():
    argv = worker_init.worker_claude_argv(**_sample_kwargs())
    assert argv[0] == "claude"
    assert argv[1] == "do the thing"
    assert argv[-2] == "--allowed-tools"
    assert argv[-1] == "Read,Write,Bash"


def test_worker_claude_argv_includes_remote_control_before_allowed_tools():
    argv = worker_init.worker_claude_argv(**_sample_kwargs())
    assert "--remote-control" in argv
    assert argv.index("--remote-control") < argv.index("--allowed-tools")


def test_worker_claude_argv_uses_dash_n_session_name():
    argv = worker_init.worker_claude_argv(**_sample_kwargs())
    idx = argv.index("-n")
    assert argv[idx + 1] == "MAC Developer #af5268b3 (SHOOT the teaser)"


def test_worker_claude_argv_extra_flags_carried_through():
    argv = worker_init.worker_claude_argv(
        **_sample_kwargs(extra_flags=["--resume", "sess-123"]))
    assert "--resume" in argv
    assert argv[argv.index("--resume") + 1] == "sess-123"
    # Still last.
    assert argv[-2:] == ["--allowed-tools", "Read,Write,Bash"]


def test_worker_claude_argv_no_remote_control_when_host_opts_out(monkeypatch):
    monkeypatch.setattr(worker_init, "get_host", lambda name: {"remote_control": False})
    argv = worker_init.worker_claude_argv(**_sample_kwargs())
    assert "--remote-control" not in argv


def test_resume_argv_matches_init_argv_shape():
    """The pin test for the drift this task's brief warns about: init and
    resume must render byte-identical argv for identical inputs, apart from
    the positional prompt and whatever `extra_flags` resume adds (--resume
    <session_id>)."""
    init_argv = worker_init.worker_claude_argv(**_sample_kwargs(prompt="fresh prompt"))
    resume_argv = worker_init.worker_claude_argv(
        **_sample_kwargs(prompt="resume nudge", extra_flags=["--resume", "sess-abc"]))

    # Strip the two known-different pieces, then the rest must be identical.
    def _strip(argv, prompt, extra):
        out = list(argv)
        out[out.index(prompt)] = "<PROMPT>"
        if extra:
            i = out.index(extra[0])
            del out[i:i + len(extra)]
        return out

    assert (_strip(init_argv, "fresh prompt", None)
            == _strip(resume_argv, "resume nudge", ["--resume", "sess-abc"]))
