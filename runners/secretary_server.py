"""Secretary HTTP server — task-0d26cf7d (+ SPEC-CHANGE.md, same task).

An OpenAI-chat-compatible shim so the Telegram webhook (mooniex-claudeflow,
running inside a Docker container on Contabo) can turn one chat message into
one `claude` CLI run without ever spawning `claude` itself. Same shape as the
existing Hermes API server: a host-side process bound to a fixed host/port,
called over HTTP with a bearer key.

Security boundary, per the CEO's mid-task SPEC-CHANGE.md: LungNote gets FULL
read/write (add/complete/cancel/delete/create/append) — "a secretary that
cannot write things down is not a secretary." Everything else stays
observe-and-note-only: Bash/Write/Edit/NotebookEdit are denied, every
mcp__org__* task-lifecycle tool is denied, and the `org` MCP server is never
even registered (see config/secretary.mcp.json), so those tools are
unreachable regardless of the allowlist. The safety net for the widened
LungNote surface is behavioural, not code: the system prompt below enforces
confirm-before-write / report-after-write (SPEC-CHANGE.md Change 3).

Endpoint:  POST /v1/chat/completions   (OpenAI chat-completion shape)
Auth:      Authorization: Bearer $SECRETARY_API_KEY  (required — refuses to
           start if unset)
Bind:      $SECRETARY_HOST:$SECRETARY_PORT (default 127.0.0.1:8643 — 8642 is
           Hermes, do not reuse it)

`claude` flags settled on (verified live against `claude --help` + a handful
of real -p runs on this box, claude 2.1.231):
  -p "<prompt>" --output-format json     JSON result on stdout; top-level
                                          "session_id" and "result" fields.
                                          No per-tool-call breakdown in this
                                          format (only "json (single
                                          result)" per --help) — see
                                          SPEC-CHANGE.md Change 4 note below.
  --permission-mode dontAsk              Confirmed via `claude --help`
                                          (choices include dontAsk) and via
                                          the CLI's own internal messaging
                                          ("DontAsk mode is handled in main
                                          permission flow", distinct from
                                          bypassPermissions) — a headless run
                                          with this mode does not block
                                          waiting for interactive approval.
  --allowed-tools <comma-list>           Only ALLOWED_TOOLS below.
  --system-prompt <SECRETARY_SYSTEM_PROMPT>
                                          Full replace, not --append — the
                                          secretary must not inherit Claude
                                          Code's default coding-agent persona.
  --mcp-config <secretary.mcp.json> --strict-mcp-config
                                          Only the lungnote server, ignoring
                                          any ambient MCP config.
  --resume <session-id>                  Only when we have one on record for
                                          this conversation. Verified live: a
                                          stale/unknown session id exits 1
                                          with "No conversation found with
                                          session ID: ..." on stderr — see
                                          run_secretary_turn()'s fallback.

SPEC-CHANGE.md Change 4 (audit log for LungNote writes) — SKIPPED. A live
`-p --output-format json` run (verified on this box) returns a single
aggregated result object (session_id, result, usage/cost, etc.) with no list
of tool calls made during the run; per-tool-call events only exist in
`--output-format stream-json`, which the spec change explicitly says not to
switch to just for this ("do not build a wrapper... that is a separate
task"). Documented here and in the task report rather than skipped silently.

Run:  python -m runners.secretary_server
"""
from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.logger import get_logger  # noqa: E402

# ---------------------------------------------------------------------------
# Config — all env-overridable, defaults per TASK.md deliverables 1-2.
# ---------------------------------------------------------------------------
SECRETARY_HOST = os.environ.get("SECRETARY_HOST", "127.0.0.1")
SECRETARY_PORT = int(os.environ.get("SECRETARY_PORT", "8643"))
SECRETARY_API_KEY = os.environ.get("SECRETARY_API_KEY", "")
SECRETARY_WORKDIR = os.environ.get("SECRETARY_WORKDIR", str(ROOT))
SECRETARY_TIMEOUT_SECONDS = int(os.environ.get("SECRETARY_TIMEOUT_SECONDS", "180"))
SECRETARY_MAX_CONCURRENT = int(os.environ.get("SECRETARY_MAX_CONCURRENT", "1"))

CLAUDE_BIN = os.environ.get("SECRETARY_CLAUDE_BIN", "claude")

# Mac path is the fallback default; ensure_mcp_config() re-resolves this
# (env LUNGNOTE_MCP_PATH first) and rewrites the generated config at startup.
DEFAULT_LUNGNOTE_MCP_PATH = "/Users/gob/LungNote Projects/mcp/index.js"

# Both of these are rewritten at runtime, so a deployment must be able to put
# them outside the checkout. Under systemd the server runs as a service user
# with no write access to a root-owned repo — that is exactly how this first
# crashed on Contabo (PermissionError on config/secretary.mcp.json). Writing
# into the repo would also leave it permanently dirty, because the resolved
# lungnote path differs per host.
MCP_CONFIG_PATH = Path(
    os.environ.get("SECRETARY_MCP_CONFIG") or ROOT / "config" / "secretary.mcp.json"
)
SESSION_DB_PATH = Path(
    os.environ.get("SECRETARY_SESSION_DB") or ROOT / "state" / "secretary_sessions.db"
)

ERROR_PREFIX = "⚠️ เลขาขัดข้อง: "

# ---------------------------------------------------------------------------
# Deliverable 3 — the tool allowlist. THE SECURITY CORE.
#
# Anything NOT listed here is denied. Per SPEC-CHANGE.md Change 1, LungNote
# gets its FULL surface (reads + writes, including delete_todo/cancel_todo,
# which the original brief forbade — that restriction is REVERSED). Change 2
# keeps everything else forbidden: Bash, Write, Edit, NotebookEdit, and every
# mcp__org__* task-lifecycle tool — the org MCP server is not even
# registered (config/secretary.mcp.json), so those are unreachable
# regardless of this list. The real guard is
# test_allowlist_never_contains_a_mutating_or_org_tool in
# scripts/test_secretary_server.py, not this comment — adding a Bash/Write/
# Edit/NotebookEdit/mcp__org__* name here needs CEO sign-off.
# ---------------------------------------------------------------------------
ALLOWED_TOOLS: tuple[str, ...] = (
    "mcp__lungnote__list_todos",
    "mcp__lungnote__read_note",
    "mcp__lungnote__search_notes",
    "mcp__lungnote__list_recent",
    "mcp__lungnote__add_todo",
    "mcp__lungnote__complete_todo",
    "mcp__lungnote__cancel_todo",
    "mcp__lungnote__delete_todo",
    "mcp__lungnote__create_note",
    "mcp__lungnote__append_note",
)

# Deliverable 5 + SPEC-CHANGE.md Change 3 — the secretary's own identity and
# its confirm-before-write / report-after-write contract. Every token here
# is paid on every single message, but Change 3 must be explicit and
# imperative in Thai, so this is longer than a plain identity prompt.
SECRETARY_SYSTEM_PROMPT = (
    "คุณคือเลขาส่วนตัวของ CEO ตอบสั้น กระชับ ตรงประเด็น "
    "(CEO กำลังเดินอ่านจากมือถือ)\n"
    "หน้าที่: รายงานสถานะงาน โดยเช็ค LungNote (to-do และ deadline) "
    "ก่อนตอบทุกครั้งที่เกี่ยวกับงาน\n"
    "ถ้าไม่รู้หรือดูไม่เห็นข้อมูลส่วนไหน ให้บอกตรงๆ ว่าไม่รู้/ไม่เห็น ห้ามเดาหรือกุคำตอบ\n"
    "คุณแก้ไข/สั่งงาน/merge/delegate ใดๆ ในระบบ org ไม่ได้เลย มีแค่ LungNote เท่านั้นที่แก้ได้\n"
    "\n"
    "กฎการเขียน LungNote (add_todo, complete_todo, cancel_todo, delete_todo, "
    "create_note, append_note):\n"
    "1. ห้ามเขียนทันทีตอนที่ CEO พูดถึงครั้งแรก "
    "(เช่น \"จดไว้ว่า...\" \"ลบอันนั้นออก\" \"แก้เป็น...\") "
    "ให้พูดย้ำก่อนว่ากำลังจะเปลี่ยนอะไร (to-do/note ไหน ข้อความที่จะใส่หรือลบ) "
    "แล้วถามยืนยัน แล้วหยุดรอคำตอบ\n"
    "2. เขียนได้เฉพาะเมื่อ CEO ยืนยันชัดเจนในข้อความถัดมาเท่านั้น "
    "คำตอบที่กำกวมไม่นับเป็นการยืนยัน ให้ถามใหม่\n"
    "3. หลังเขียนเสร็จ ให้รายงานว่าเปลี่ยนอะไรจริง "
    "(เพิ่ม/แก้/ปิด/ลบ พร้อม id หรือชื่อ) เป็นบรรทัดสั้นๆ "
    "ถ้าบางส่วนล้มเหลวให้บอกว่าส่วนไหนล้มเหลว\n"
    "การอ่าน (list_todos, read_note, search_notes, list_recent) ไม่ต้องขอยืนยันก่อน\n"
)

_LOGGER: object | None = None


def _log():
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = get_logger("secretary")
    return _LOGGER


# ---------------------------------------------------------------------------
# Deliverable 4 helper — resolve + (re)write config/secretary.mcp.json so the
# one committed file works on both the Mac and Contabo. Only ever called at
# server startup (main()), never at import or per-request, and never by
# tests (which point MCP_CONFIG_PATH elsewhere if they need to).
# ---------------------------------------------------------------------------

def resolve_lungnote_path() -> str:
    return os.environ.get("LUNGNOTE_MCP_PATH", DEFAULT_LUNGNOTE_MCP_PATH)


def ensure_mcp_config() -> Path:
    config = {
        "mcpServers": {
            "lungnote": {
                "type": "stdio",
                "command": "node",
                "args": [resolve_lungnote_path()],
                "env": {},
            }
        }
    }
    MCP_CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    return MCP_CONFIG_PATH


# ---------------------------------------------------------------------------
# Session continuity — conversation_id -> claude session id. This is also
# what makes SPEC-CHANGE.md Change 3 work: the "here's what I'll change"
# propose turn and the "yes" confirm turn are two messages resumed in the
# same claude session, so the model remembers what it proposed.
# ---------------------------------------------------------------------------

def _session_conn() -> sqlite3.Connection:
    SESSION_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SESSION_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            session_id      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )"""
    )
    return conn


def get_session_id(conversation_id: str) -> str | None:
    with _session_conn() as conn:
        row = conn.execute(
            "SELECT session_id FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
    return row[0] if row else None


def set_session_id(conversation_id: str, session_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _session_conn() as conn:
        conn.execute(
            """INSERT INTO conversations (conversation_id, session_id, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(conversation_id) DO UPDATE SET
                 session_id = excluded.session_id,
                 updated_at = excluded.updated_at""",
            (conversation_id, session_id, now),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Deliverable 2 — the claude invocation.
# ---------------------------------------------------------------------------

def _build_claude_cmd(prompt: str, session_id: str | None) -> list[str]:
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--output-format", "json",
        "--permission-mode", "dontAsk",
        "--allowed-tools", ",".join(ALLOWED_TOOLS),
        "--system-prompt", SECRETARY_SYSTEM_PROMPT,
        "--mcp-config", str(MCP_CONFIG_PATH),
        "--strict-mcp-config",
    ]
    if session_id:
        cmd += ["--resume", session_id]
    return cmd


def _run_claude_once(prompt: str, session_id: str | None) -> tuple[int, str, str, bool]:
    """Run one `claude -p` invocation. Returns (returncode, stdout, stderr,
    timed_out). Never raises for a subprocess-level failure — only for
    something like the binary not existing at all, which the caller catches.

    cwd is always SECRETARY_WORKDIR — never caller-controlled. env is
    inherited (not copied/filtered) on purpose: Contabo's ANTHROPIC_BASE_URL
    / ANTHROPIC_AUTH_TOKEN (Z.ai GLM) must reach the subprocess without this
    file hardcoding a provider.
    """
    proc = subprocess.Popen(
        _build_claude_cmd(prompt, session_id),
        cwd=SECRETARY_WORKDIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,  # own process group, so a timeout can kill the whole tree
    )
    try:
        stdout, stderr = proc.communicate(timeout=SECRETARY_TIMEOUT_SECONDS)
        return proc.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        return -1, stdout, stderr, True


def _friendly_error(reason: str) -> str:
    return f"{ERROR_PREFIX}{reason}"


def run_secretary_turn(prompt: str, conversation_id: str) -> str:
    """Run one turn for conversation_id. Never raises — every failure mode
    (bad exit code, unparseable output, timeout, stale --resume) becomes a
    friendly Thai error string instead of a 5xx or a hang (deliverable 2).
    """
    logger = _log()
    session_id = get_session_id(conversation_id)

    try:
        rc, stdout, stderr, timed_out = _run_claude_once(prompt, session_id)
    except Exception as exc:  # binary missing, permission error, etc.
        logger.error("secretary: could not launch claude subprocess: %r", exc)
        return _friendly_error("เรียกใช้งานไม่สำเร็จ")

    if timed_out:
        logger.error("secretary: timed out after %ss (conversation=%s)",
                     SECRETARY_TIMEOUT_SECONDS, conversation_id)
        return _friendly_error(f"หมดเวลา ({SECRETARY_TIMEOUT_SECONDS}s) ไม่ตอบสนอง")

    # A stale/deleted --resume session id fails fast (verified live: exit 1,
    # "No conversation found with session ID: ..." on stderr, nothing on
    # stdout). Fall back to a fresh session exactly once instead of erroring.
    if rc != 0 and session_id is not None:
        logger.warning("secretary: resume failed for conversation=%s (rc=%s, "
                       "stderr=%s) - retrying with a fresh session",
                       conversation_id, rc, stderr[:300])
        try:
            rc, stdout, stderr, timed_out = _run_claude_once(prompt, None)
        except Exception as exc:
            logger.error("secretary: retry launch failed: %r", exc)
            return _friendly_error("เรียกใช้งานไม่สำเร็จ")
        if timed_out:
            logger.error("secretary: retry timed out (conversation=%s)", conversation_id)
            return _friendly_error(f"หมดเวลา ({SECRETARY_TIMEOUT_SECONDS}s) ไม่ตอบสนอง")

    if rc != 0:
        logger.error("secretary: claude exited %s (conversation=%s) stderr=%s",
                     rc, conversation_id, stderr[:500])
        return _friendly_error("เรียกใช้งานไม่สำเร็จ (exit code ผิดปกติ)")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        logger.error("secretary: unparseable claude output (conversation=%s): %r raw=%s",
                     conversation_id, exc, stdout[:500])
        return _friendly_error("อ่านผลลัพธ์ไม่ได้")

    new_session_id = data.get("session_id")
    if new_session_id:
        set_session_id(conversation_id, new_session_id)

    if data.get("is_error"):
        logger.error("secretary: claude reported is_error (conversation=%s): %s",
                     conversation_id, json.dumps(data)[:500])
        return _friendly_error("ประมวลผลไม่สำเร็จ")

    content = data.get("result")
    if not content or not str(content).strip():
        logger.error("secretary: empty result (conversation=%s): %s",
                     conversation_id, json.dumps(data)[:500])
        return _friendly_error("ไม่มีคำตอบ")

    return str(content)


# ---------------------------------------------------------------------------
# Concurrency gate — cap actual claude subprocesses at SECRETARY_MAX_CONCURRENT
# with a small bounded queue; beyond that, reject immediately with the
# friendly error instead of piling up processes on a 4-CPU box.
# ---------------------------------------------------------------------------
_QUEUE_SLACK = 4
_concurrency_lock = threading.Lock()
_pending = 0
_slot = threading.Semaphore(SECRETARY_MAX_CONCURRENT)


def _try_acquire_slot() -> bool:
    global _pending
    with _concurrency_lock:
        if _pending >= SECRETARY_MAX_CONCURRENT + _QUEUE_SLACK:
            return False
        _pending += 1
        return True


def _release_slot() -> None:
    global _pending
    with _concurrency_lock:
        _pending -= 1


# ---------------------------------------------------------------------------
# Deliverable 1 — the HTTP server.
# ---------------------------------------------------------------------------

def check_api_key_or_exit() -> None:
    if not SECRETARY_API_KEY:
        print("SECRETARY_API_KEY is not set - refusing to start unauthenticated.",
             file=sys.stderr)
        raise SystemExit(1)


def _chat_completion(content: str, model: str) -> dict:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _last_user_message(messages: list) -> str | None:
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content")
            if content:
                return str(content)
    return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # route to our logger, not stderr
        _log().info("http: " + fmt, *args)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        return self.headers.get("Authorization", "") == f"Bearer {SECRETARY_API_KEY}"

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "not found"}})
            return

        if not self._authorized():
            self._send_json(401, {"error": {"message": "unauthorized"}})
            return

        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": {"message": "invalid JSON body"}})
            return

        prompt = _last_user_message(body.get("messages") or [])
        if not prompt:
            self._send_json(400, {"error": {"message": "no user message in messages[]"}})
            return

        # 'user' field or X-Conversation-Id header identifies the
        # conversation; "default" if neither is present. Caller never gets
        # to choose the working directory or model — only the prompt.
        conversation_id = str(
            body.get("user") or self.headers.get("X-Conversation-Id") or "default"
        )

        if not _try_acquire_slot():
            content = _friendly_error(
                "คิวเต็ม กรุณาลองใหม่อีกครั้งใน 1-2 นาที"
            )
        else:
            try:
                _slot.acquire()
                try:
                    content = run_secretary_turn(prompt, conversation_id)
                except Exception:
                    # Last-resort net: run_secretary_turn already shapes its
                    # own failures, this only catches a bug in that shaping.
                    _log().exception("secretary: unhandled error (conversation=%s)",
                                     conversation_id)
                    content = _friendly_error("เกิดข้อผิดพลาดไม่ทราบสาเหตุ")
                finally:
                    _slot.release()
            finally:
                _release_slot()

        # stream:true is accepted but ignored — streaming is out of scope,
        # we always answer with one full non-streamed chat-completion.
        self._send_json(200, _chat_completion(content, body.get("model") or "secretary"))

    def do_GET(self) -> None:
        self._send_json(404, {"error": {"message": "not found"}})


def main() -> None:
    check_api_key_or_exit()
    ensure_mcp_config()
    server = ThreadingHTTPServer((SECRETARY_HOST, SECRETARY_PORT), Handler)
    _log().info("secretary listening on %s:%s (max_concurrent=%s workdir=%s)",
               SECRETARY_HOST, SECRETARY_PORT, SECRETARY_MAX_CONCURRENT, SECRETARY_WORKDIR)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
