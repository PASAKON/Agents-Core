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
import logging
import os
import sys
import time
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
#
# task-2a135187 D1-D3 add three more: list_terminals/session_history are
# pure reads like read_session; open_terminal opens a real iTerm window on
# the Mac (not a pure read), and gets the confirm-before-call contract in
# SECRETARY_SYSTEM_PROMPT instead.
RELAY_TOOLS = (
    "mcp__relay__mac_status", "mcp__relay__org_snapshot",
    "mcp__relay__relay_to_session", "mcp__relay__spawn_c_level",
    "mcp__relay__read_session",
    "mcp__relay__list_terminals", "mcp__relay__session_history",
    "mcp__relay__open_terminal",
    # task-df6de4d4 D4: read side of the CEO-order obligation ledger. Read-only
    # — it lists rows, and takes no path, command, or role from the caller.
    "mcp__relay__list_ceo_orders",
    # task-166dfbe8 (CEO order #40): fetch a URL, report what it says. Read-only
    # — takes only `url`, no header/method/raw-HTML passthrough — SSRF-guarded
    # and its content is fenced against prompt injection in lib/link_reader.py.
    "mcp__relay__read_link",
    # task-c7d455aa (CEO follow-up to order #40): download the video behind a
    # link and file it into the CEO's Drive. NOT a pure read (writes a file to
    # Drive) but no confirm gate — the CEO's own link IS the instruction, per
    # SECRETARY_SYSTEM_PROMPT's grab_video rule.
    "mcp__relay__grab_video",
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


def test_bare_kept_when_auth_comes_from_an_env_token(monkeypatch) -> None:
    """--bare roughly halves turn latency (measured on Contabo: 8.3-10.7s with
    it vs 15.6-17.4s without, same prompt with a tool call). Dropping it when
    it WOULD have worked is a silent 2x regression — the reply text looks
    identical — so pin it for the env-token path (Z.ai and any
    ANTHROPIC_API_KEY setup)."""
    monkeypatch.delenv("SECRETARY_BARE", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok-from-env")
    assert "--bare" in ss._build_claude_cmd("hello", None)

    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key-from-env")
    assert "--bare" in ss._build_claude_cmd("hello", None)


def test_bare_dropped_when_auth_is_the_oauth_credential_file(monkeypatch) -> None:
    """THE regression this guards. --bare also skips reading
    ~/.claude/.credentials.json, so on the Claude OAuth subscription it does
    not merely slow the turn down — it breaks it outright. Proven by A/B on
    Contabo 2026-08-14: with --bare the CLI answered "Not logged in · Please
    run /login" (is_error=true) while the identical command without it
    answered normally. No env token means OAuth, which means no --bare."""
    monkeypatch.delenv("SECRETARY_BARE", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert "--bare" not in ss._build_claude_cmd("hello", None)


def test_bare_can_be_forced_either_way(monkeypatch) -> None:
    """An operator escape hatch for a setup the heuristic does not know
    about — in both directions, so it can also be turned OFF on an env-token
    setup (e.g. to debug whether --bare is implicated in something)."""
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok-from-env")
    monkeypatch.setenv("SECRETARY_BARE", "off")
    assert "--bare" not in ss._build_claude_cmd("hello", None)

    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("SECRETARY_BARE", "on")
    assert "--bare" in ss._build_claude_cmd("hello", None)


def test_flags_after_bare_are_present_regardless_of_the_bare_decision(monkeypatch) -> None:
    """The refactor that made --bare conditional split one flat list into
    two concatenated halves. A slip there would silently drop the allowlist
    or the system prompt — i.e. hand the Telegram-reachable secretary its
    DEFAULT tool set. Assert the tail survives on both branches."""
    monkeypatch.delenv("SECRETARY_BARE", raising=False)
    for token, expect_bare in (("tok", True), (None, False)):
        if token:
            monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", token)
        else:
            monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
            monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cmd = ss._build_claude_cmd("hello", None)
        assert ("--bare" in cmd) is expect_bare
        for flag in ("--allowed-tools", "--system-prompt",
                     "--mcp-config", "--strict-mcp-config"):
            assert flag in cmd, f"{flag} lost when bare={expect_bare}"


def test_system_prompt_tells_the_model_to_page_past_the_default_limit() -> None:
    """list_todos defaults to 50 rows. With no explicit limit the secretary
    answered "50" when the CEO actually had 127 open to-dos: a status bot
    under-reporting by 2.5x while sounding certain. This instruction is the
    only thing preventing it, so assert it survives prompt edits."""
    assert "limit=200" in ss.SECRETARY_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# task-2a135187 D4 -- the six explicit rules TASK.md requires, each pinned
# because it has already gone wrong once for real.
# ---------------------------------------------------------------------------

def test_system_prompt_states_middleman_only_rule() -> None:
    """Rule 1: never do the work, never fix a problem, never edit anything
    -- the CEO's own constraint, outranks being helpful."""
    assert "ตัวกลาง" in ss.SECRETARY_SYSTEM_PROMPT
    assert "ห้ามเริ่มลงมือทำงานเอง" in ss.SECRETARY_SYSTEM_PROMPT


def test_system_prompt_states_ceo_instruction_only_rule() -> None:
    """Rule 2: only on the CEO's own instruction -- never spawn/relay/open
    a terminal on the secretary's own initiative."""
    assert "โดยจากการสั่งของ CEO เท่านั้น" in ss.SECRETARY_SYSTEM_PROMPT


def test_system_prompt_states_never_claim_unused_capability_rule() -> None:
    """Rule 3: never claim a capability not actually used -- SomPong once
    told the CEO it could run shell commands, then refused when asked."""
    assert "รันคำสั่งเชลล์ได้" in ss.SECRETARY_SYSTEM_PROMPT
    assert "ห้ามเดาว่าทำได้" in ss.SECRETARY_SYSTEM_PROMPT


def test_system_prompt_states_partial_answer_must_be_labelled_rule() -> None:
    """Rule 4: complete=false must be said, never silently merged into a
    Contabo-only picture presented as the whole org."""
    assert "complete=false" in ss.SECRETARY_SYSTEM_PROMPT


def test_system_prompt_states_percent_null_means_unknown_rule() -> None:
    """Rule 6: percent: null means unknown, never round down to 0%, never
    estimate from session age."""
    assert "percent" in ss.SECRETARY_SYSTEM_PROMPT
    assert "ยังไม่รู้ %" in ss.SECRETARY_SYSTEM_PROMPT
    assert "ห้ามปัดเป็น 0%" in ss.SECRETARY_SYSTEM_PROMPT


def test_system_prompt_covers_the_three_new_relay_tools_by_name() -> None:
    for name in ("list_terminals", "session_history", "open_terminal"):
        assert name in ss.SECRETARY_SYSTEM_PROMPT, f"{name} missing from the prompt"


def test_system_prompt_covers_grab_video_by_name_and_its_key_rules() -> None:
    """D7 -- what it does, that it's not a pure read but needs no extra
    confirmation, that the reported link must be real (never invented),
    and that a failure must be stated plainly (never smoothed into
    'กำลังโหลดอยู่')."""
    assert "grab_video" in ss.SECRETARY_SYSTEM_PROMPT
    assert "drive_link" in ss.SECRETARY_SYSTEM_PROMPT
    assert "ห้ามเดาหรือแต่งลิงก์ขึ้นมาเองเด็ดขาด" in ss.SECRETARY_SYSTEM_PROMPT
    assert "กำลังโหลดอยู่" in ss.SECRETARY_SYSTEM_PROMPT


def test_system_prompt_splits_session_star_family() -> None:
    """/session-open etc. must be relayed to the live session, not executed
    directly; /session-list must be answered from list_terminals."""
    assert "relay_to_session" in ss.SECRETARY_SYSTEM_PROMPT
    assert "/session-open" in ss.SECRETARY_SYSTEM_PROMPT
    assert "list_terminals" in ss.SECRETARY_SYSTEM_PROMPT


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


def test_api_error_skips_the_useless_resume_retry(running_server) -> None:
    """Live-verified 2026-08-14: a Z.ai 5h-quota rejection produces rc=1,
    empty stderr, and an `api_error_status` on the stdout JSON. Retrying with
    a fresh session cannot help a rate limit -- it is per-account, not
    per-session -- so the fix must call the stub exactly ONCE (not twice,
    like the stale-resume path above) and surface the CLI's own message,
    which already names the reset time.
    """
    url, set_stub = running_server
    calls: list = []

    def fn(prompt, session_id):
        calls.append(session_id)
        return (1, json.dumps({
            "is_error": True, "api_error_status": 429,
            "result": "API Error: Request rejected (429) - Usage limit "
                      "reached for 5 hour. Your limit will reset at "
                      "2026-08-15 05:30:02",
        }), "", False)

    set_stub(fn)
    conv = "conv-ratelimited"
    ss.set_session_id(conv, "some-existing-session")

    status, payload = _post(url, _chat_body("ping", conv))
    assert status == 200
    content = payload["choices"][0]["message"]["content"]
    assert content.startswith(ss.ERROR_PREFIX)
    assert "05:30:02" in content, "the CLI's own reset time must reach the CEO"
    assert calls == ["some-existing-session"], (
        "a rate limit must not trigger the fresh-session retry -- it would "
        "just burn another ~180s hitting the same limit again"
    )
    # A dead session id from a rate-limited turn is still worth keeping --
    # unlike the stale-resume case, nothing here proved the session itself
    # is bad, so overwriting it would be a guess.
    assert ss.get_session_id(conv) == "some-existing-session"


def test_api_error_on_the_fresh_retry_is_also_recognized(running_server) -> None:
    """The same check applies after the stale-resume fallback fires: if the
    ORIGINAL failure was a genuine stale session (not a rate limit), but the
    fresh retry then hits a rate limit, that must be reported honestly too
    instead of falling through to the generic exit-code message."""
    url, set_stub = running_server
    calls: list = []

    def fn(prompt, session_id):
        calls.append(session_id)
        if session_id is not None:
            return (1, "", "No conversation found with session ID: " + session_id, False)
        return (1, json.dumps({
            "is_error": True, "api_error_status": 429,
            "result": "Usage limit reached for 5 hour. Your limit will "
                      "reset at 2026-08-15 05:30:02",
        }), "", False)

    set_stub(fn)
    conv = "conv-stale-then-ratelimited"
    ss.set_session_id(conv, "dead-session-id")

    status, payload = _post(url, _chat_body("continue please", conv))
    assert status == 200
    content = payload["choices"][0]["message"]["content"]
    assert content.startswith(ss.ERROR_PREFIX)
    assert "05:30:02" in content
    assert calls == ["dead-session-id", None]


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


# ---------------------------------------------------------------------------
# 6. D1 (task-870f70f8) — _extract_api_error widened past api_error_status
# ---------------------------------------------------------------------------

def test_extract_api_error_still_recognizes_the_429_shape() -> None:
    """The original narrow gate this widened from — must stay green."""
    stdout = json.dumps({
        "is_error": True, "api_error_status": 429,
        "result": "Usage limit reached for 5 hour. Your limit will reset "
                  "at 2026-08-15 05:30:02",
    })
    assert ss._extract_api_error(stdout) == (
        "Usage limit reached for 5 hour. Your limit will reset at "
        "2026-08-15 05:30:02"
    )


def test_extract_api_error_recognizes_oauth_expired_with_null_api_error_status() -> None:
    """Live shape from 2026-08-15: api_error_status is null, but
    terminal_reason and result both explain exactly what happened. The
    original api_error_status-only gate missed this; the widened one must
    not."""
    stdout = json.dumps({
        "is_error": True, "api_error_status": None,
        "terminal_reason": "api_error",
        "result": "Failed to authenticate: OAuth session expired and "
                  "could not be refreshed",
    })
    assert ss._extract_api_error(stdout) == (
        "Failed to authenticate: OAuth session expired and could not be refreshed"
    )


def test_extract_api_error_returns_none_for_a_failed_run_with_no_usable_text() -> None:
    assert ss._extract_api_error(json.dumps({
        "is_error": True, "api_error_status": None,
        "terminal_reason": None, "result": "",
    })) is None
    assert ss._extract_api_error(json.dumps({"is_error": True})) is None
    assert ss._extract_api_error("") is None


def test_extract_api_error_caps_a_multi_kb_result() -> None:
    huge = "x" * 5000
    result = ss._extract_api_error(json.dumps({
        "is_error": True, "api_error_status": 500, "result": huge,
    }))
    assert result is not None
    assert len(result) == ss.API_ERROR_MAX_CHARS


def test_a_successful_run_never_routes_through_the_error_path(running_server) -> None:
    """A successful run also has a `result` (the actual answer). This must
    only ever surface via _extract_api_error on a FAILED run -- enforced by
    rc == 0 short-circuiting before _extract_api_error is ever called in
    run_secretary_turn, not by anything inside _extract_api_error itself."""
    url, set_stub = running_server
    set_stub(lambda prompt, session_id: (
        0, json.dumps({"session_id": "s1", "is_error": False,
                       "result": "the actual answer"}), "", False))
    status, payload = _post(url, _chat_body("ping"))
    assert status == 200
    content = payload["choices"][0]["message"]["content"]
    assert content == "the actual answer"
    assert not content.startswith(ss.ERROR_PREFIX)


# ---------------------------------------------------------------------------
# 7. D2 (task-870f70f8) — per-turn provider resolution via pick_provider
# ---------------------------------------------------------------------------

def test_resolve_provider_env_picks_zai_and_sets_child_env(monkeypatch) -> None:
    monkeypatch.setattr(ss, "pick_provider", lambda token: "zai")
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-key")
    env, reason = ss._resolve_provider_env()
    assert env["ANTHROPIC_BASE_URL"] == ss._PROVIDER_ENDPOINTS["zai"]
    assert env["ANTHROPIC_AUTH_TOKEN"] == "test-zai-key"
    assert env["ANTHROPIC_MODEL"] == ss._PROVIDER_DEFAULT_MODEL["zai"]
    assert "zai" in reason
    # --bare must follow the resolved provider in the SAME call, not
    # whatever the parent process's os.environ happens to say.
    assert ss._bare_is_safe(env) is True


def test_resolve_provider_env_picks_claude_and_clears_any_stale_zai_pin(monkeypatch) -> None:
    """The exact failure this D2 fixes: the service file pinned Z.ai, but
    quota picked Claude for this turn -- the child env must not still carry
    the Z.ai vars, or it would silently keep talking to Z.ai anyway."""
    monkeypatch.setattr(ss, "pick_provider", lambda token: "claude")
    # Pinned, not inherited from the box: whether this machine happens to hold
    # a live Claude credential must not decide whether this test passes.
    monkeypatch.setattr(ss, "_claude_auth_available", lambda: True)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.z.ai/api/anthropic")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "stale-zai-token")
    monkeypatch.setenv("ANTHROPIC_MODEL", "glm-5.2")
    env, reason = ss._resolve_provider_env()
    assert "ANTHROPIC_BASE_URL" not in env
    assert "ANTHROPIC_AUTH_TOKEN" not in env
    assert "ANTHROPIC_MODEL" not in env
    assert "claude" in reason
    # No token left in env -> OAuth path -> --bare must follow, in this SAME call.
    assert ss._bare_is_safe(env) is False


def test_claude_with_dead_oauth_falls_back_to_zai(monkeypatch) -> None:
    """THE regression this guards, hit in production within hours of shipping
    the quota router: pick_provider measures HEADROOM, never usability. Claude
    had the most headroom on the secretary box so it was picked every turn, and
    every turn died on "OAuth session expired and could not be refreshed" while
    Z.ai sat idle with a working key. Headroom is not usability."""
    monkeypatch.setattr(ss, "pick_provider", lambda token: "claude")
    monkeypatch.setattr(ss, "_claude_auth_available", lambda: False)
    monkeypatch.setenv(ss._PROVIDER_KEY_VAR["zai"], "live-zai-key")

    env, reason = ss._resolve_provider_env()

    assert env["ANTHROPIC_BASE_URL"] == ss._PROVIDER_ENDPOINTS["zai"]
    assert env["ANTHROPIC_AUTH_TOKEN"] == "live-zai-key"
    assert "fell back to zai" in reason
    # An env token is present -> --bare is safe again, decided in this same call.
    assert ss._bare_is_safe(env) is True


def test_claude_dead_and_no_zai_key_keeps_inherited_env(monkeypatch) -> None:
    """Both providers unusable is not a reason to invent one. Keep the
    inherited env and say so — the turn may still fail, but it fails with the
    real upstream error rather than one this function manufactured."""
    monkeypatch.setattr(ss, "pick_provider", lambda token: "claude")
    monkeypatch.setattr(ss, "_claude_auth_available", lambda: False)
    monkeypatch.setattr(ss, "_read_dotenv_var", lambda name: None)
    monkeypatch.delenv(ss._PROVIDER_KEY_VAR["zai"], raising=False)

    _env, reason = ss._resolve_provider_env()

    assert "no ZAI_API_KEY" in reason
    assert "kept inherited env" in reason


def test_claude_auth_available_is_false_for_an_expired_credential(monkeypatch, tmp_path) -> None:
    """Existence is not validity. The file that caused the outage was present
    and well formed; only its expiry gave it away."""
    cred = tmp_path / "creds.json"
    monkeypatch.setenv("CLAUDE_CREDENTIALS_PATH", str(cred))

    cred.write_text(json.dumps({"claudeAiOauth": {"expiresAt": 1_000}}))  # 1970
    assert ss._claude_auth_available() is False

    far_future_ms = (time.time() + 86_400) * 1000
    cred.write_text(json.dumps({"claudeAiOauth": {"expiresAt": far_future_ms}}))
    assert ss._claude_auth_available() is True

    cred.write_text("not json at all")
    assert ss._claude_auth_available() is False

    cred.unlink()
    assert ss._claude_auth_available() is False


def test_resolve_provider_env_falls_back_when_zai_key_missing(monkeypatch) -> None:
    monkeypatch.setattr(ss, "pick_provider", lambda token: "zai")
    # Also stub the .env fallback -- a real ZAI_API_KEY in this box's actual
    # repo-root .env must not leak into the test regardless of the env var.
    monkeypatch.setattr(ss, "_read_dotenv_var", lambda name: None)
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.setenv("SOME_MARKER_VAR", "keep-me")
    env, reason = ss._resolve_provider_env()
    assert env == dict(os.environ)
    assert env["SOME_MARKER_VAR"] == "keep-me"
    assert "no ZAI_API_KEY" in reason


def test_resolve_provider_env_falls_back_when_pick_provider_raises(monkeypatch) -> None:
    def boom(token):
        raise RuntimeError("ssh unreachable")
    monkeypatch.setattr(ss, "pick_provider", boom)
    env, reason = ss._resolve_provider_env()
    assert env == dict(os.environ)
    assert "unavailable" in reason


def test_resolve_provider_env_falls_back_on_unrecognised_provider(monkeypatch) -> None:
    monkeypatch.setattr(ss, "pick_provider", lambda token: "bogus-provider")
    env, reason = ss._resolve_provider_env()
    assert env == dict(os.environ)
    assert "unrecognised" in reason


def test_resolve_provider_env_does_not_block_the_turn_when_pick_provider_hangs(monkeypatch) -> None:
    """Never block a turn on the quota check: pick_provider running long past
    SECRETARY_QUOTA_TIMEOUT_SECONDS must not stall the caller past that bound.
    No real SSH/HTTP here -- pick_provider itself is stubbed."""
    monkeypatch.setattr(ss, "SECRETARY_QUOTA_TIMEOUT_SECONDS", 0.05)

    def hangs(token):
        time.sleep(0.4)
        return "claude"

    monkeypatch.setattr(ss, "pick_provider", hangs)
    start = time.monotonic()
    env, reason = ss._resolve_provider_env()
    elapsed = time.monotonic() - start
    assert elapsed < 0.3, "must not block the turn waiting for a slow quota check"
    assert env == dict(os.environ)
    assert "unavailable" in reason


def test_run_claude_once_logs_which_provider_and_why(monkeypatch) -> None:
    """A reviewer must be able to answer 'which provider did this turn use,
    and why' from the log alone. Attaches a handler directly to the
    "secretary" logger rather than using caplog -- that logger sets
    propagate=False (lib/logger.py), so records never reach caplog's
    root-logger handler."""
    monkeypatch.setattr(ss, "pick_provider", lambda token: "claude")

    class _FakeProc:
        returncode = 0

        def communicate(self, timeout=None):
            return json.dumps({"result": "ok", "is_error": False}), ""

    monkeypatch.setattr(ss.subprocess, "Popen", lambda *a, **k: _FakeProc())

    messages: list[str] = []
    handler = logging.Handler()
    handler.emit = lambda record: messages.append(record.getMessage())
    secretary_logger = logging.getLogger("secretary")
    secretary_logger.addHandler(handler)
    try:
        ss._run_claude_once("hi", None)
    finally:
        secretary_logger.removeHandler(handler)

    assert any("provider for this turn" in m and "claude" in m for m in messages)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
