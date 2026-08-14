"""Tests for runners/secretary_server.py (task-0d26cf7d + SPEC-CHANGE.md).

Every test stubs `_run_claude_once` — no real `claude` subprocess, no
network, no real LungNote MCP call. Real state (state/tasks.db, the real
state/secretary_sessions.db, the real config/secretary.mcp.json) is never
touched: SESSION_DB_PATH and MCP_CONFIG_PATH are monkeypatched to tmp_path
for every test that needs them (ADR 0021 §1).

Covers Deliverable 6 items 1-5 plus the SPEC-CHANGE.md Change 5 update to
the allowlist test. There is deliberately no test for the confirm-before-
write / report-after-write behavioural contract (SPEC-CHANGE.md Change 3)
— it lives entirely in SECRETARY_SYSTEM_PROMPT text, not in code, so there
is nothing for a unit test to assert without faking a live model reply.
SPEC-CHANGE.md Change 4 (audit log) was skipped in the implementation (see
secretary_server.py's module docstring), so there is no test for it either.

Run standalone: python scripts/test_secretary_server.py
Or under pytest:  pytest scripts/test_secretary_server.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import runners.secretary_server as ss  # noqa: E402

API_KEY = "test-secret-key"
URL_PATH = "/v1/chat/completions"

# Forbidden per TASK.md Deliverable 3 (unchanged by SPEC-CHANGE.md Change 2):
# fs/exec tools and every org task-lifecycle tool. LungNote's delete_todo/
# cancel_todo used to be on this list too — SPEC-CHANGE.md Change 1 reversed
# that, so they are asserted PRESENT below, not absent.
FORBIDDEN_TOOLS = (
    "Bash", "Write", "Edit", "NotebookEdit",
    "mcp__org__create_task", "mcp__org__delegate_task",
    "mcp__org__delegate_parallel_tasks", "mcp__org__merge_task",
    "mcp__org__revert_task_tool", "mcp__org__reopen_task",
    "mcp__org__close_dev", "mcp__org__wiki_write",
)

# Full LungNote surface, required present per SPEC-CHANGE.md Change 1.
REQUIRED_LUNGNOTE_TOOLS = (
    "mcp__lungnote__list_todos", "mcp__lungnote__read_note",
    "mcp__lungnote__search_notes", "mcp__lungnote__list_recent",
    "mcp__lungnote__add_todo", "mcp__lungnote__complete_todo",
    "mcp__lungnote__cancel_todo", "mcp__lungnote__delete_todo",
    "mcp__lungnote__create_note", "mcp__lungnote__append_note",
)

# Named proxy actions added by task-b293ef6c so the secretary can act for the
# CEO without a shell. Each is a fixed action with typed arguments — none
# accepts a command, shell string, or caller-supplied path. Adding a name here
# grants a real capability; it is meant to require a deliberate edit.
#
# mcp__relay__read_session arrived with task-da873c76 (read-only, closes the
# round-trip gap: relay_to_session/spawn_c_level could act but nothing could
# read a session back). No confirm-before-write needed since it changes
# nothing; still deliberately listed here rather than inferred.
RELAY_TOOLS = (
    "mcp__relay__mac_status", "mcp__relay__org_snapshot",
    "mcp__relay__relay_to_session", "mcp__relay__spawn_c_level",
    "mcp__relay__read_session",
)


# ---------------------------------------------------------------------------
# 1. Allowlist guard — the security boundary itself.
# ---------------------------------------------------------------------------

def test_allowlist_never_contains_a_mutating_or_org_tool() -> None:
    """SECURITY BOUNDARY: a mis-tap on a phone must never reach Bash/Write/
    Edit/NotebookEdit or any mcp__org__* tool (merge_task, delegate_task,
    ...). This is the guard the module comment on ALLOWED_TOOLS points at —
    if this test is green, the allowlist constant cannot smuggle one of
    those names in, no matter what the comment says.
    """
    for forbidden in FORBIDDEN_TOOLS:
        assert forbidden not in ss.ALLOWED_TOOLS, (
            f"{forbidden!r} must never appear in ALLOWED_TOOLS")

    for required in REQUIRED_LUNGNOTE_TOOLS:
        assert required in ss.ALLOWED_TOOLS, (
            f"{required!r} is part of LungNote's full surface "
            "(SPEC-CHANGE.md Change 1) and must be present")

    # And nothing sneaked in beyond the reviewed surface. Deliberately kept as
    # exact equality: an "allowlist" that only screens for known-bad names
    # stops being an allowlist the moment someone adds a name nobody thought
    # to forbid. Widening this set is the act of granting the secretary a new
    # capability, and should be as visible in review as one.
    #
    # RELAY_TOOLS arrived with task-b293ef6c: four *named* proxy actions (Mac
    # liveness, org snapshot, relay an order to a C-level session, spawn one).
    # None of them takes a shell string, a command, or a caller-supplied path
    # — that property is enforced in scripts/test_relay_mcp_server.py.
    assert set(ss.ALLOWED_TOOLS) == set(REQUIRED_LUNGNOTE_TOOLS) | set(RELAY_TOOLS)


def test_generated_mcp_config_never_carries_a_cwd_key(tmp_path, monkeypatch) -> None:
    """Claude Code silently drops an mcpServers entry carrying a `cwd` key.

    Nothing surfaces the failure. The server still starts by hand, its
    `initialize` and `tools/list` both answer correctly, and the tools simply
    never reach the session — no error on either side. It cost a deploy to
    find on Contabo, and the only symptom the CEO saw was the secretary
    saying it had no such tool.

    Launch by absolute path instead: the module puts its own repo root on
    sys.path from __file__, so it needs no working directory.
    """
    monkeypatch.setattr(ss, "MCP_CONFIG_PATH", tmp_path / "secretary.mcp.json")
    written = json.loads(ss.ensure_mcp_config().read_text())

    for name, entry in written["mcpServers"].items():
        assert "cwd" not in entry, (
            f"mcpServers[{name!r}] carries a 'cwd' key — Claude Code drops the "
            "whole server without logging anything")
        assert entry["args"], f"mcpServers[{name!r}] has no args"

    relay = written["mcpServers"]["relay"]
    assert "-m" not in relay["args"], "`-m` needs a cwd; use an absolute path"
    assert relay["args"][0].endswith("relay_mcp_server.py")


def test_build_claude_cmd_omits_resume_when_session_id_none() -> None:
    cmd = ss._build_claude_cmd("hello", None)
    assert "--resume" not in cmd


def test_build_claude_cmd_includes_resume_flag_when_session_id_given() -> None:
    cmd = ss._build_claude_cmd("hello", "sess-abc-123")
    assert cmd[-2:] == ["--resume", "sess-abc-123"]


def test_build_claude_cmd_keeps_bare_flag() -> None:
    """--bare roughly halves turn latency (measured on Contabo: 8.3-10.7s with
    it vs 15.6-17.4s without, same prompt with a tool call). Dropping it is a
    silent 2x regression — the reply text looks identical — so pin it."""
    assert "--bare" in ss._build_claude_cmd("hello", None)


def test_system_prompt_tells_the_model_to_page_past_the_default_limit() -> None:
    """list_todos defaults to 50 rows. With no explicit limit the secretary
    answered "50" when the CEO actually had 127 open to-dos: a status bot
    under-reporting by 2.5x while sounding certain. This instruction is the
    only thing preventing it, so assert it survives prompt edits."""
    assert "limit=200" in ss.SECRETARY_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def running_server(tmp_path, monkeypatch):
    """Real ThreadingHTTPServer on an OS-assigned port, backed by a
    monkeypatched session DB under tmp_path and a stubbed claude subprocess.
    Yields (base_url, set_stub) where set_stub(fn) installs
    fn(prompt, session_id) -> (rc, stdout, stderr, timed_out) as the stand-in
    for _run_claude_once.
    """
    monkeypatch.setattr(ss, "SECRETARY_API_KEY", API_KEY)
    monkeypatch.setattr(ss, "SESSION_DB_PATH", tmp_path / "secretary_sessions.db")
    monkeypatch.setattr(ss, "SECRETARY_MAX_CONCURRENT", 1)
    monkeypatch.setattr(ss, "_slot", ss.threading.Semaphore(1))
    monkeypatch.setattr(ss, "_pending", 0)

    stub_holder = {"fn": lambda prompt, session_id: (
        0, json.dumps({"session_id": "unused", "result": "ok", "is_error": False}), "", False)}

    def _stub(prompt, session_id):
        return stub_holder["fn"](prompt, session_id)

    monkeypatch.setattr(ss, "_run_claude_once", _stub)

    def set_stub(fn):
        stub_holder["fn"] = fn

    server = ss.ThreadingHTTPServer((ss.SECRETARY_HOST, 0), ss.Handler)
    thread = ss.threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        yield f"http://127.0.0.1:{port}{URL_PATH}", set_stub
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _post(url: str, body: dict, *, bearer: str | None = API_KEY,
         conversation_header: str | None = None):
    headers = {"Content-Type": "application/json"}
    if bearer is not None:
        headers["Authorization"] = f"Bearer {bearer}"
    if conversation_header is not None:
        headers["X-Conversation-Id"] = conversation_header
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        try:
            return exc.code, json.loads(payload)
        except json.JSONDecodeError:
            return exc.code, {}


def _chat_body(text: str, conversation_id: str | None = None) -> dict:
    body = {"model": "secretary", "messages": [{"role": "user", "content": text}],
           "stream": False}
    if conversation_id is not None:
        body["user"] = conversation_id
    return body


# ---------------------------------------------------------------------------
# 2. Auth
# ---------------------------------------------------------------------------

def test_missing_bearer_returns_401(running_server) -> None:
    url, _ = running_server
    status, _ = _post(url, _chat_body("hi"), bearer=None)
    assert status == 401


def test_wrong_bearer_returns_401(running_server) -> None:
    url, _ = running_server
    status, _ = _post(url, _chat_body("hi"), bearer="not-the-right-key")
    assert status == 401


def test_correct_bearer_returns_200(running_server) -> None:
    url, set_stub = running_server
    set_stub(lambda prompt, session_id: (
        0, json.dumps({"session_id": "s1", "result": "pong", "is_error": False}), "", False))
    status, payload = _post(url, _chat_body("ping"))
    assert status == 200
    assert payload["choices"][0]["message"]["content"] == "pong"
    assert payload["object"] == "chat.completion"


# ---------------------------------------------------------------------------
# 3. Refuses to start without SECRETARY_API_KEY
# ---------------------------------------------------------------------------

def test_refuses_to_start_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(ss, "SECRETARY_API_KEY", "")
    with pytest.raises(SystemExit) as exc_info:
        ss.check_api_key_or_exit()
    assert exc_info.value.code == 1


def test_starts_fine_with_api_key_set(monkeypatch) -> None:
    monkeypatch.setattr(ss, "SECRETARY_API_KEY", "some-key")
    ss.check_api_key_or_exit()  # must not raise


# ---------------------------------------------------------------------------
# 4. Failure shaping — never a raised exception, never 5xx, always 200 with
#    a friendly Thai-prefixed message.
# ---------------------------------------------------------------------------

def test_nonzero_exit_becomes_friendly_200(running_server) -> None:
    url, set_stub = running_server
    set_stub(lambda prompt, session_id: (1, "", "boom", False))
    status, payload = _post(url, _chat_body("do something"))
    assert status == 200
    content = payload["choices"][0]["message"]["content"]
    assert content.startswith(ss.ERROR_PREFIX)


def test_unparseable_output_becomes_friendly_200(running_server) -> None:
    url, set_stub = running_server
    set_stub(lambda prompt, session_id: (0, "not valid json {{{", "", False))
    status, payload = _post(url, _chat_body("do something"))
    assert status == 200
    content = payload["choices"][0]["message"]["content"]
    assert content.startswith(ss.ERROR_PREFIX)


def test_timeout_becomes_friendly_200(running_server) -> None:
    url, set_stub = running_server
    set_stub(lambda prompt, session_id: (-1, "", "", True))
    status, payload = _post(url, _chat_body("do something slow"))
    assert status == 200
    content = payload["choices"][0]["message"]["content"]
    assert content.startswith(ss.ERROR_PREFIX)


def test_stale_resume_falls_back_to_fresh_session(running_server) -> None:
    """SPEC/deliverable 2: a stale --resume session id must not surface as
    an error — it retries fresh once and the fresh result is what the CEO
    sees, with the NEW session id recorded (not left pointing at the dead
    one).
    """
    url, set_stub = running_server
    calls: list = []

    def fn(prompt, session_id):
        calls.append(session_id)
        if session_id is not None:
            return (1, "", "No conversation found with session ID: " + session_id, False)
        return (0, json.dumps({"session_id": "brand-new-session", "result": "recovered",
                              "is_error": False}), "", False)

    set_stub(fn)
    conv = "conv-stale"
    # Seed a stale session id directly in the DB (as if a previous turn had
    # recorded one that later got deleted/expired).
    ss.set_session_id(conv, "dead-session-id")

    status, payload = _post(url, _chat_body("continue please", conv))
    assert status == 200
    assert payload["choices"][0]["message"]["content"] == "recovered"
    assert calls == ["dead-session-id", None]
    assert ss.get_session_id(conv) == "brand-new-session"


# ---------------------------------------------------------------------------
# 5. Session mapping
# ---------------------------------------------------------------------------

def test_first_message_records_session_id(running_server) -> None:
    url, set_stub = running_server
    calls: list = []

    def fn(prompt, session_id):
        calls.append(session_id)
        return (0, json.dumps({"session_id": "sess-first", "result": "hi there",
                              "is_error": False}), "", False)

    set_stub(fn)
    conv = "conv-A"
    status, _ = _post(url, _chat_body("hello", conv))
    assert status == 200
    assert calls == [None]  # first message: no prior session, no --resume
    assert ss.get_session_id(conv) == "sess-first"


def test_second_message_passes_resume_with_recorded_id(running_server) -> None:
    url, set_stub = running_server
    calls: list = []

    def fn(prompt, session_id):
        calls.append(session_id)
        return (0, json.dumps({"session_id": "sess-first", "result": "reply",
                              "is_error": False}), "", False)

    set_stub(fn)
    conv = "conv-B"
    _post(url, _chat_body("first message", conv))
    _post(url, _chat_body("follow-up message", conv))
    assert calls == [None, "sess-first"]


def test_different_conversation_does_not_reuse_session(running_server) -> None:
    url, set_stub = running_server
    calls: list = []

    def fn(prompt, session_id):
        calls.append((prompt, session_id))
        sid = "sess-" + prompt  # unique per conversation for this test
        return (0, json.dumps({"session_id": sid, "result": "reply",
                              "is_error": False}), "", False)

    set_stub(fn)
    _post(url, _chat_body("convA-msg", "conv-A2"))
    _post(url, _chat_body("convB-msg", "conv-B2"))
    # Neither conversation's first turn should have resumed the other's session.
    assert calls == [("convA-msg", None), ("convB-msg", None)]
    assert ss.get_session_id("conv-A2") == "sess-convA-msg"
    assert ss.get_session_id("conv-B2") == "sess-convB-msg"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
