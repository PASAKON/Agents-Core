"""Unit tests for tools/remote_worker_log.py (GH #152 iteration 2).

No real ssh: subprocess.run is monkeypatched throughout. Covers the
summariser (all 4 entry types), secret masking, missing-transcript,
ssh-failure, and the measured Windows slug rule.

Run via: pytest scripts/test_remote_worker_log.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.remote_worker_log as rwl  # noqa: E402

WINBOX_HOST_CFG = {"ssh": "winbox", "os": "windows", "worktrees": r"C:\Users\UsEr\mooniex\worktrees"}


# ---------------------------------------------------------------------------
# slug building (measured on winbox 2026-09-18)
# ---------------------------------------------------------------------------

def test_cwd_slug_matches_measured_winbox_example():
    path = r"C:\Users\UsEr\mooniex\worktrees\mooniex-agents__browser_operator__task-424077a4"
    expected = "C--Users-UsEr-mooniex-worktrees-mooniex-agents--browser-operator--task-424077a4"
    assert rwl._cwd_slug(path) == expected


def test_cwd_slug_replaces_one_for_one_never_collapses():
    assert rwl._cwd_slug("a__b") == "a--b"
    assert rwl._cwd_slug("a_b") == "a-b"
    assert rwl._cwd_slug("C:") == "C-"


# ---------------------------------------------------------------------------
# secret masking
# ---------------------------------------------------------------------------

# Deliberately low-entropy, obviously-not-real placeholder tokens (repeated
# words, not random hex) -- exercises _SECRET_RE's fixed pattern match
# without tripping a scanner's entropy heuristics on a real-looking secret.
_FAKE_SK = "sk-notarealsecretnotreal"
_FAKE_GHP = "ghp_notarealsecretnotreal"
_FAKE_JWT = "eyJnotarealsecretnotrealtoken"


def test_mask_secrets_redacts_known_prefixes():
    text = f"key={_FAKE_SK} token={_FAKE_GHP} jwt={_FAKE_JWT}"
    masked = rwl._mask_secrets(text)
    assert _FAKE_SK not in masked
    assert _FAKE_GHP not in masked
    assert _FAKE_JWT not in masked
    assert masked.count("***") == 3


def test_mask_secrets_leaves_normal_text_alone():
    text = "this is a normal log line with no secrets in it"
    assert rwl._mask_secrets(text) == text


def test_preview_masks_and_truncates():
    long_secret = "sk-" + "notreal" * 6
    out = rwl._preview(long_secret, 10)
    assert "***" in out
    assert len(out) <= 10 or out == "***"


# ---------------------------------------------------------------------------
# JSONL summarisation -- all 4 entry types
# ---------------------------------------------------------------------------

def _line(obj: dict) -> str:
    return json.dumps(obj)


def test_entries_from_jsonl_summarizes_all_types():
    raw = "\n".join([
        _line({
            "type": "user", "timestamp": "2026-09-18T10:00:00.000Z",
            "message": {"role": "user", "content": "please check the login page"},
        }),
        _line({
            "type": "assistant", "timestamp": "2026-09-18T10:00:05.000Z",
            "message": {"role": "assistant", "content": [
                {"type": "text", "text": "Sure, checking now."},
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "ls -la"}},
            ]},
        }),
        _line({
            "type": "user", "timestamp": "2026-09-18T10:00:06.000Z",
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": [{"type": "text", "text": "total 0"}]},
            ]},
        }),
        _line({
            "type": "user", "timestamp": "2026-09-18T10:00:07.000Z",
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t2", "is_error": True,
                 "content": "command not found"},
            ]},
        }),
    ])
    entries = rwl._entries_from_jsonl(raw)
    labels = [e[1] for e in entries]
    assert labels == ["user", "assistant-text", "tool_use", "tool_result", "tool_result"]

    assert entries[0] == ("10:00:00", "user", "please check the login page")
    assert entries[1] == ("10:00:05", "assistant-text", "Sure, checking now.")
    assert entries[2][1] == "tool_use"
    assert entries[2][2].startswith("Bash, ")
    assert entries[3] == ("10:00:06", "tool_result", "ok, total 0")
    assert entries[4] == ("10:00:07", "tool_result", "error, command not found")


def test_entries_from_jsonl_skips_malformed_lines():
    raw = "\n".join([
        "not json at all",
        _line({"type": "user", "timestamp": "2026-09-18T10:00:00.000Z",
              "message": {"role": "user", "content": "hello"}}),
        "{broken json",
    ])
    entries = rwl._entries_from_jsonl(raw)
    assert len(entries) == 1
    assert entries[0][2] == "hello"


def test_entries_from_jsonl_masks_secrets_in_tool_use_input():
    raw = _line({
        "type": "assistant", "timestamp": "2026-09-18T10:00:00.000Z",
        "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash",
             "input": {"command": f"curl -H 'Authorization: {_FAKE_SK}'"}},
        ]},
    })
    entries = rwl._entries_from_jsonl(raw)
    assert _FAKE_SK not in entries[0][2]
    assert "***" in entries[0][2]


def test_entries_from_jsonl_empty_content_produces_nothing():
    raw = _line({"type": "user", "timestamp": "2026-09-18T10:00:00.000Z",
                "message": {"role": "user", "content": ""}})
    assert rwl._entries_from_jsonl(raw) == []


# ---------------------------------------------------------------------------
# _fetch_transcript_tail -- ssh mocked
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_fetch_transcript_tail_success(monkeypatch):
    task = {"id": "task-abc", "host": "winbox", "project": "mooniex-agents",
           "role": "developer"}
    monkeypatch.setattr(rwl, "get_host", lambda name: WINBOX_HOST_CFG)
    fake_jsonl = _line({"type": "user", "timestamp": "2026-09-18T10:00:00.000Z",
                        "message": {"role": "user", "content": "hi"}})
    monkeypatch.setattr(
        rwl.subprocess, "run",
        lambda *a, **k: _FakeResult(0, stdout=fake_jsonl),
    )
    out = rwl._fetch_transcript_tail(task)
    assert out == fake_jsonl


def test_fetch_transcript_tail_uses_encoded_command_not_raw_pipe(monkeypatch):
    """Regression guard (measured live on winbox 2026-09-18): a raw
    `-Command <script with |>` gets its pipe characters consumed by the
    remote host's outer shell before powershell.exe ever sees it -- ssh
    joins argv into one string, and `Sort-Object`/`Select-Object` were split
    off as their own "commands" and failed with "'Sort-Object' is not
    recognized...". -EncodedCommand (base64, no shell-special characters)
    is the fix; this must never regress back to a piped -Command."""
    task = {"id": "task-abc", "host": "winbox", "project": "mooniex-agents",
           "role": "developer"}
    monkeypatch.setattr(rwl, "get_host", lambda name: WINBOX_HOST_CFG)
    captured = {}

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeResult(0, stdout="{}")

    monkeypatch.setattr(rwl.subprocess, "run", _fake_run)
    rwl._fetch_transcript_tail(task)

    cmd = captured["cmd"]
    assert "-EncodedCommand" in cmd
    assert "-Command" not in cmd
    # No argv element may contain a raw pipe -- that's the whole bug class.
    assert not any("|" in part for part in cmd)


def test_fetch_transcript_tail_no_transcript_raises_lookup_error(monkeypatch):
    task = {"id": "task-abc", "host": "winbox", "project": "mooniex-agents",
           "role": "developer"}
    monkeypatch.setattr(rwl, "get_host", lambda name: WINBOX_HOST_CFG)
    monkeypatch.setattr(
        rwl.subprocess, "run",
        lambda *a, **k: _FakeResult(2, stdout="NO_TRANSCRIPT"),
    )
    try:
        rwl._fetch_transcript_tail(task)
        assert False, "expected LookupError"
    except LookupError as e:
        assert "no transcript exists yet" in str(e)


def test_fetch_transcript_tail_ssh_failure_raises_connection_error(monkeypatch):
    task = {"id": "task-abc", "host": "winbox", "project": "mooniex-agents",
           "role": "developer"}
    monkeypatch.setattr(rwl, "get_host", lambda name: WINBOX_HOST_CFG)

    def _raise(*a, **k):
        raise OSError("no route to host")
    monkeypatch.setattr(rwl.subprocess, "run", _raise)
    try:
        rwl._fetch_transcript_tail(task)
        assert False, "expected ConnectionError"
    except ConnectionError as e:
        assert "ssh to winbox failed" in str(e)


def test_fetch_transcript_tail_nonzero_exit_raises_connection_error(monkeypatch):
    task = {"id": "task-abc", "host": "winbox", "project": "mooniex-agents",
           "role": "developer"}
    monkeypatch.setattr(rwl, "get_host", lambda name: WINBOX_HOST_CFG)
    monkeypatch.setattr(
        rwl.subprocess, "run",
        lambda *a, **k: _FakeResult(1, stderr="something broke"),
    )
    try:
        rwl._fetch_transcript_tail(task)
        assert False, "expected ConnectionError"
    except ConnectionError as e:
        assert "something broke" in str(e)


def test_fetch_transcript_tail_mac_host_raises_value_error(monkeypatch):
    task = {"id": "task-abc", "host": "mac", "project": "mooniex-agents",
           "role": "developer"}
    monkeypatch.setattr(rwl, "get_host", lambda name: {"ssh": None, "os": "darwin"})
    try:
        rwl._fetch_transcript_tail(task)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "no ssh needed" in str(e)


def test_fetch_transcript_tail_linux_host_raises_value_error(monkeypatch):
    task = {"id": "task-abc", "host": "contabo", "project": "mooniex-agents",
           "role": "developer"}
    monkeypatch.setattr(rwl, "get_host",
                        lambda name: {"ssh": "mooniex-vps", "os": "linux"})
    try:
        rwl._fetch_transcript_tail(task)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "only windows/winbox today" in str(e)


def test_fetch_transcript_tail_missing_worktree_fields_raises_value_error(monkeypatch):
    task = {"id": "task-abc", "host": "winbox"}  # no project/role
    monkeypatch.setattr(rwl, "get_host", lambda name: WINBOX_HOST_CFG)
    try:
        rwl._fetch_transcript_tail(task)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "could not build a worktree path" in str(e)


# ---------------------------------------------------------------------------
# _resolve_task -- uses the real (test) tasks.db
# ---------------------------------------------------------------------------

def test_resolve_task_exact_id(monkeypatch, tmp_path):
    import lib.db as db_mod
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init()
    tid = db_mod.create_task(project="mooniex-agents", role="developer",
                             title="t", description="d", owner_cto=None)
    task = rwl._resolve_task(tid)
    assert task["id"] == tid


def test_resolve_task_not_found_raises_value_error(monkeypatch, tmp_path):
    import lib.db as db_mod
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init()
    try:
        rwl._resolve_task("task-doesnotexist")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "no task matching" in str(e)

def test_mask_leaves_task_ids_alone():
    # `sk` inside `task-95803168` must not trigger the mask (live false
    # positive on the first E2E run, 2026-09-18).
    from tools.remote_worker_log import _mask_secrets
    assert _mask_secrets("# Task task-95803168 on winbox") == "# Task task-95803168 on winbox"
    assert _mask_secrets("key sk-abcdefghijkl here") == "key *** here"
    assert _mask_secrets("token ghp_abcdefghijklmnop") == "token ***"
