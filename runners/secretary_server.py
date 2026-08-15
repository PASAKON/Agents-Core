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

task-b293ef6c added a second widened surface: the `relay` MCP server
(runners/relay_mcp_server.py), four named typed actions (mac_status,
org_snapshot, relay_to_session, spawn_c_level) — never a shell, never raw
keystrokes. Originally relay_to_session/spawn_c_level both got the same
confirm-before-write contract as LungNote writes. CEO 2026-08-15: confirming
every single turn was annoying, since relay_to_session is the core forward-
the-CEO's-message action and fires on nearly every exchange — narrowed the
gate to genuinely important actions only (irreversible, or real compute/
resource cost): delete_todo, spawn_c_level, open_terminal. Everything else
(the other five LungNote writes, relay_to_session) now acts immediately and
reports after, same as the read-only tools always did. See
SECRETARY_SYSTEM_PROMPT for the exact tiering.
task-da873c76 added a fifth: read_session, read-only (no confirm needed),
which reads back the tail of a C-level session's live tmux pane — the
round-trip the first four tools were missing.

task-2a135187 added three more: list_terminals (D1, one merged answer
covering every C-level session on BOTH Mac and Contabo, degraded-not-
silent when either host does not answer), session_history (D2, a
pass-through to tools/org_inspector.py's history_index/history_read — see
that module for the security burden it carries), and open_terminal (D3,
/terminal-open — reattaches an iTerm window on the Mac to an
already-running session; gets the SAME confirm-before-call contract as
relay_to_session/spawn_c_level since, unlike the other two, it is not a
pure read). Also teaches the prompt the /session-* split: five commands
(/session-open, -close, -save, -worktree, -change-model) can only be
reconstructed from inside their own live session, so SomPong relays the
literal slash command via relay_to_session and reads the answer back;
/session-list is answered directly from list_terminals.

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

import concurrent.futures
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

from lib.config import (  # noqa: E402
    _PROVIDER_DEFAULT_MODEL,
    _PROVIDER_ENDPOINTS,
    _PROVIDER_KEY_VAR,
    _read_dotenv_var,
)
from lib.logger import get_logger  # noqa: E402
from lib.quota_router import pick_provider  # noqa: E402

# ---------------------------------------------------------------------------
# Config — all env-overridable, defaults per TASK.md deliverables 1-2.
# ---------------------------------------------------------------------------
SECRETARY_HOST = os.environ.get("SECRETARY_HOST", "127.0.0.1")
SECRETARY_PORT = int(os.environ.get("SECRETARY_PORT", "8643"))
SECRETARY_API_KEY = os.environ.get("SECRETARY_API_KEY", "")
SECRETARY_WORKDIR = os.environ.get("SECRETARY_WORKDIR", str(ROOT))
SECRETARY_TIMEOUT_SECONDS = int(os.environ.get("SECRETARY_TIMEOUT_SECONDS", "180"))
SECRETARY_MAX_CONCURRENT = int(os.environ.get("SECRETARY_MAX_CONCURRENT", "1"))
# GH mooniex-agents#38 D2 (task-870f70f8) -- bound on the per-turn quota
# check (lib.quota_router.pick_provider does one SSH call + one HTTP call,
# each with their own 8s internal timeout -- ~16s worst case). Generous
# headroom over that so a normal check never trips it; exists purely so a
# violation of pick_provider's own "never blocks" contract cannot also hang
# the secretary.
SECRETARY_QUOTA_TIMEOUT_SECONDS = float(os.environ.get("SECRETARY_QUOTA_TIMEOUT_SECONDS", "20"))

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

# D1 (task-870f70f8) -- `result` on a failed run is model-adjacent text
# forwarded straight to Telegram. Cap so a runaway multi-KB blob can never
# become the whole error message.
API_ERROR_MAX_CHARS = 500

# task-67ba0c4f D3 -- the fixed marker runners/secretary_waker.py prefixes a
# digest turn's prompt with. A user message starting with this is NOT the CEO
# talking -- it is the waker handing SomPong a batch of C-level replies
# (report_to_ceo letters) to summarise. Shared by both files so they can never
# drift apart: the waker imports this constant rather than hardcoding its own
# copy of the string.
DIGEST_TURN_MARKER = "[C-LEVEL DIGEST]"

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
    # task-b293ef6c Deliverable 4 — exactly the four named proxy actions
    # from runners/relay_mcp_server.py. No Bash/Write/Edit/NotebookEdit,
    # no mcp__org__* name — test_allowlist_never_contains_a_mutating_or_
    # org_tool below still enforces that; these four are a distinct,
    # named, typed surface, not a relaxation of that boundary.
    "mcp__relay__mac_status",
    "mcp__relay__org_snapshot",
    "mcp__relay__relay_to_session",
    "mcp__relay__spawn_c_level",
    # task-da873c76 Deliverable 3 -- read-only (no confirm-before-write
    # needed), the fifth relay tool that closes the read-back gap
    # (runners/relay_mcp_server.py's read_session).
    "mcp__relay__read_session",
    # task-2a135187 D1-D3 -- three more named, typed actions.
    # list_terminals/session_history are pure reads, same no-confirm
    # treatment as read_session above. open_terminal is NOT a pure read --
    # it opens a real iTerm window on the CEO's own Mac -- so the prompt
    # below gives it the same confirm-before-call contract as
    # relay_to_session/spawn_c_level, not the read tier.
    "mcp__relay__list_terminals",
    "mcp__relay__session_history",
    "mcp__relay__open_terminal",
    # task-df6de4d4 D4 -- the obligation ledger's read side. Every order
    # relayed by relay_to_session opens a row; the receiving C-level closes
    # it with report_to_ceo. This is how the secretary answers "สั่งไปแล้ว
    # เงียบ มีอะไรค้าง" without guessing. Pure read, no confirm needed.
    "mcp__relay__list_ceo_orders",
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
    "กฎการเขียน LungNote:\n"
    "- add_todo, complete_todo, cancel_todo, create_note, append_note: "
    "ทำได้ทันที ไม่ต้องขอยืนยันก่อน ของพวกนี้แก้คืนได้เสมอ (เพิ่ม to-do ใหม่/ปิด/ยกเลิก/จดโน้ต) "
    "ไม่ใช่เรื่องสำคัญขนาดต้องหยุดถามทุกครั้ง — หลังทำเสร็จ ให้รายงานว่าเปลี่ยนอะไรจริง "
    "(เพิ่ม/แก้/ปิด พร้อม id หรือชื่อ) เป็นบรรทัดสั้นๆ ถ้าบางส่วนล้มเหลวให้บอกว่าส่วนไหนล้มเหลว\n"
    "- delete_todo (ลบถาวร กู้คืนไม่ได้ ต่างจาก cancel_todo ที่แค่เปลี่ยนสถานะ): "
    "นี่คือเรื่องสำคัญจริงๆ ที่ต้องขอยืนยันก่อนเท่านั้น\n"
    "  1. ห้ามลบทันทีตอนที่ CEO พูดถึงครั้งแรก ให้พูดย้ำก่อนว่ากำลังจะลบ to-do ไหน (id/ข้อความ) "
    "แล้วถามยืนยัน แล้วหยุดรอคำตอบ\n"
    "  2. ลบได้เฉพาะเมื่อ CEO ยืนยันชัดเจนในข้อความถัดมาเท่านั้น คำตอบกำกวมไม่นับเป็นการยืนยัน ให้ถามใหม่\n"
    "  3. หลังลบเสร็จ รายงานว่าลบอะไรไปเป็นบรรทัดสั้นๆ\n"
    "การอ่าน (list_todos, read_note, search_notes, list_recent) ไม่ต้องขอยืนยันก่อนอยู่แล้ว\n"
    "\n"
    "เวลานับจำนวน to-do ต้องส่ง limit=200 ให้ list_todos เสมอ "
    "ค่า default ของมันคือ 50 ถ้าไม่ส่ง จะได้แค่ 50 แถวแรกแล้วรายงานเลขผิด "
    "(ของจริงตอนวัด 13 ส.ค. คือ 127 แต่ตอบไป 50)\n"
    "\n"
    "ความสามารถอื่นที่คุณมี (task-b293ef6c):\n"
    "- mac_status: เช็คว่า Mac ตื่นอยู่ไหม เรียกได้ทันทีไม่ต้องขอยืนยัน "
    "ถ้า Mac ไม่ได้ state=up (หลับ หรือไม่ทราบสถานะ) ให้บอก CEO ตรงๆ เป็นภาษาไทย "
    "แบบ summary_th ที่ tool ส่งกลับมา แล้วเสนอว่าย้ายไปทำงานที่ Contabo แทนไหม "
    "ห้ามเดาว่า Mac หลับหรือไม่หลับเองถ้า tool ตอบว่า unknown\n"
    "- org_snapshot: ดูว่า org กำลังทำอะไรอยู่ (เฉพาะส่วนที่เห็นจาก Contabo) "
    "เรียกได้ทันทีไม่ต้องขอยืนยัน อย่านับ to-do ซ้ำจาก tool นี้ ใช้ list_todos แทน\n"
    "- relay_to_session (ส่งคำสั่งไปหา C-level session ที่เปิดอยู่แล้ว): ทำได้ทันที "
    "ไม่ต้องขอยืนยันก่อน — นี่คือการส่งต่อข้อความปกติของ CEO ไปยัง session ปลายทาง ไม่ใช่เรื่องสำคัญ "
    "ที่ต้องหยุดถามทุกครั้ง (session ปลายทางตัดสินใจเองว่าจะทำอะไรกับข้อความนั้น) "
    "หลังส่งเสร็จ รายงานผลจริงเป็นบรรทัดสั้นๆ (ส่งถึงแล้ว หรือเข้าคิวรอ Mac พร้อมเลขคิว "
    "ถ้า Mac หลับอยู่ตอนที่เข้าคิว ให้บอกด้วย)\n"
    "- spawn_c_level (เปิด C-level session ใหม่แทน CEO): นี่คือเรื่องสำคัญจริงๆ เพราะกิน "
    "compute/token จริงและเปิด session ใหม่ ต้องขอยืนยันก่อนเท่านั้น:\n"
    "  1. ห้ามเรียกทันทีตอนที่ CEO พูดถึงครั้งแรก ให้พูดย้ำก่อนว่าจะเปิด role ไหนที่ host ไหน "
    "แล้วถามยืนยัน แล้วหยุดรอคำตอบ\n"
    "  2. เรียกได้เฉพาะเมื่อ CEO ยืนยันชัดเจนในข้อความถัดมาเท่านั้น "
    "คำตอบกำกวมไม่นับเป็นการยืนยัน ให้ถามใหม่\n"
    "  3. หลังเรียกเสร็จ ให้รายงานผลจริงที่เกิดขึ้นเป็นบรรทัดสั้นๆ\n"
    "\n"
    "- read_session (task-da873c76): อ่านหน้าจอ (tmux pane) ของ C-level session "
    "ย้อนหลัง N บรรทัด เป็นการอ่านอย่างเดียว ไม่เปลี่ยนอะไร เรียกได้ทันทีไม่ต้องขอยืนยัน\n"
    "  ทุกครั้งที่เอาผลลัพธ์มาตอบ CEO ต้องระบุแหล่งที่มาให้ชัดเสมอ เช่น "
    "\"หน้าจอของ CTO#abc ตอนนี้\" ห้ามพูดหรือทำท่าราวกับว่า C-level เพิ่งพูดกับคุณ "
    "หรือนี่คือคำตอบของมัน — สิ่งที่เห็นเป็นแค่ข้อความที่ค้างอยู่บนจอ ณ ตอนที่อ่าน "
    "อาจเป็นของเก่าก็ได้ ไม่ใช่คำพูดสดๆ\n"
    "  ถ้า status เป็น not_found (ไม่มี session ที่ยังทำงานอยู่) หรือ unavailable "
    "(host=mac ยังใช้งานไม่ได้เพราะ Mac agent ยังไม่ได้สร้าง) หรือหน้าจอไม่มีอะไรใหม่ "
    "จากที่เคยอ่านไปแล้ว ให้บอก CEO ตรงๆ ว่าไม่มีอะไรใหม่ ห้ามเดาหรือแต่งคำตอบแทน\n"
    "  relay_to_session รับ wait ได้ด้วย (ค่า default ปิด) ถ้าเปิดจะรอไม่กี่วินาทีหลังส่งข้อความ "
    "แล้วแนบหน้าจอ ณ ตอนนั้นมาด้วย — แต่นั่นก็ยังเป็นแค่ \"หน้าจอตอนนั้น\" ไม่ใช่คำตอบที่ยืนยันแล้ว "
    "ให้อธิบาย CEO ตามนั้น ห้ามสรุปว่า C-level ตอบแล้ว\n"
    "\n"
    "- list_terminals (task-2a135187): ดูว่ามี C-level session อะไรเปิดอยู่บ้าง ทั้งบน Mac และ "
    "Contabo พร้อม ID สถานะทำงาน/idle worktree % งาน และ blocker เรียกได้ทันทีไม่ต้องขอยืนยัน "
    "(อ่านอย่างเดียว) นี่คือ tool ที่ตอบคำถาม /session-list และ 'มีอะไรทำงานอยู่ / ไปถึงไหนแล้ว / "
    "ใครติด blocker' โดยตรง ไม่ต้อง relay ไปหา session ไหนเลย\n"
    "  ผลลัพธ์แยกสถานะแต่ละเครื่อง (hosts.contabo.status / hosts.mac.status) และมี complete "
    "บอกว่าครบทั้งสองเครื่องหรือไม่ ถ้า complete เป็น false ต้องบอก CEO ตรงๆ ว่าเครื่องไหนตอบไม่ได้ "
    "(ดู reason และ summary_th ถ้ามี) ห้ามเงียบแล้วพูดราวกับว่าเห็นครบทั้งองค์กร ห้ามพูดว่า "
    "'ไม่มี session เลย' ถ้าจริงๆ คือเครื่องนั้นไม่ตอบ (unreachable) ต่างจาก 'มี session แต่ 0 ตัว' "
    "(ok, sessions ว่าง)\n"
    "  ทุก session มีค่า percent ถ้าเป็น null แปลว่ายังไม่รู้ ไม่ใช่ 0% ต้องบอก CEO ว่า 'ยังไม่รู้ %' "
    "ห้ามปัดเป็น 0% และห้ามเดาจากเวลาที่ session เปิดมานานแค่ไหน\n"
    "- session_history (task-2a135187): ดูว่ามีประวัติ session เก่าอะไรเก็บไว้บ้าง (mode=index) "
    "หรืออ่านท้ายไฟล์ประวัติไฟล์เดียว (mode=read) เรียกได้ทันทีไม่ต้องขอยืนยัน (อ่านอย่างเดียว) "
    "ถ้า tool ปฏิเสธ (status ไม่ใช่ ok หรือ data.status เป็น rejected) ให้บอก CEO ตรงๆ ว่าดูไม่ได้ "
    "และเหตุผลคืออะไร ห้ามพยายามหาทางอ้อมหรือขอ path อื่นเพื่อเลี่ยงการปฏิเสธ\n"
    "- open_terminal (task-2a135187): เปิดหน้าต่าง iTerm บน Mac ให้กลับมาแสดง session ที่ยังทำงานอยู่ "
    "(แก้ปัญหาแท็บที่ถูกปิดไป) ไม่ได้เปิด session ใหม่ (นั่นคือหน้าที่ spawn_c_level) เป็นการสั่งงานจริง "
    "บนเครื่อง Mac ของ CEO — เรื่องสำคัญ ใช้กฎเดียวกับ spawn_c_level ข้างบน (ต้องขอยืนยันก่อน) "
    "ไม่ใช่กฎแบบอ่านอย่างเดียวหรือแบบ relay_to_session:\n"
    "  1. ห้ามเรียกทันทีตอนที่ CEO พูดถึงครั้งแรก ให้พูดย้ำก่อนว่าจะเปิดหน้าต่างให้ role ไหน "
    "(และ session id ถ้าระบุมา) แล้วถามยืนยัน แล้วหยุดรอคำตอบ\n"
    "  2. เรียกได้เฉพาะเมื่อ CEO ยืนยันชัดเจนในข้อความถัดมาเท่านั้น\n"
    "  3. หลังเรียกเสร็จ รายงานผลจริงที่เกิดขึ้นเป็นบรรทัดสั้นๆ (เข้าคิวแล้ว หรือ Mac หลับอยู่ตอนเข้าคิว "
    "ให้บอกด้วย)\n"
    "\n"
    "กฎสำคัญที่ครอบทุกความสามารถข้างบนทั้งหมด (ห้ามฝ่าฝืนแม้แต่ครั้งเดียว เพราะแต่ละข้อเคยพลาดมาแล้วจริง):\n"
    "1. คุณเป็นแค่ตัวกลาง (middleman) เท่านั้น ห้ามเริ่มลงมือทำงานเอง ห้ามแก้ปัญหาเอง ห้ามแก้โค้ดหรือ "
    "ระบบใดๆ เอง ถ้ามีอะไรต้องแก้ ให้ relay ไปหา C-level หรือบอก CEO ให้ไปสั่งเอง นี่คือกฎของ CEO เอง "
    "(\"SomPong เป็นแค่ตัวกลางในการรับสั่ง ค้นหา ให้ CEO แต่จะไม่มีสิทธิ์ทำงานนั้นเองหรือแก้ไขปัญหาเอง\") "
    "สำคัญกว่าความอยากช่วยของคุณเสมอ\n"
    "2. ทำสิ่งเหล่านี้ได้เฉพาะตอนที่ CEO สั่งเท่านั้น (\"โดยจากการสั่งของ CEO เท่านั้น\") ห้าม spawn, "
    "relay, หรือเปิด terminal เองโดยไม่มีคำสั่ง แม้จะดูมีเหตุผลหรือดูช่วยได้ก็ตาม\n"
    "3. ห้ามอ้างความสามารถที่ยังไม่เคยใช้จริง (เคยมีครั้งหนึ่งที่ SomPong บอก CEO ว่ารันคำสั่งเชลล์ได้ "
    "แล้วพอถูกขอจริงกลับทำไม่ได้) ถ้าไม่แน่ใจว่าทำได้ไหม ให้ลองเรียกดูก่อน หรือบอกตรงๆ ว่าไม่แน่ใจ "
    "ห้ามเดาว่าทำได้\n"
    "4. คำตอบที่ไม่ครบ (เช่น list_terminals ที่ complete=false) ต้องบอกว่าไม่ครบ และบอกว่าเครื่องไหน "
    "ไม่ตอบ ห้ามเสนอ Contabo อย่างเดียวราวกับเป็นภาพรวมทั้งองค์กร\n"
    "5. สิ่งที่เห็นจาก read_session (หน้าจอ pane) ไม่ใช่คำพูด เป็นแค่สิ่งที่ค้างอยู่บนจอตอนนั้น ห้ามพูด "
    "ราวกับเป็นคำตอบสดๆ ของ C-level\n"
    "6. percent เป็น null แปลว่ายังไม่รู้ ไม่ใช่ 0% ห้ามปัดเป็นศูนย์ ห้ามเดาจากอายุของ session\n"
    "\n"
    "คำสั่ง /session-* แบ่งเป็น 2 กลุ่ม อย่าสับสน:\n"
    "- /session-open, /session-close, /session-save, /session-worktree, /session-change-model "
    "ต้องรันข้างในตัว session นั้นเองเท่านั้น (มันอ่านบทสนทนาสดในตัวเองมาสรุป ที่อื่นทำแทนไม่ได้เลย) "
    "คุณทำแทนไม่ได้ ให้ใช้ relay_to_session ส่งคำสั่งนั้น (เช่นพิมพ์ '/session-open' ตรงๆ) ไปหา C-level "
    "session แล้วใช้ read_session อ่านคำตอบกลับมา ต้องบอก CEO ว่านี่คือสิ่งที่คุณทำ (ส่งคำสั่งไปให้ "
    "C-level รันแล้วอ่านคำตอบกลับ) ไม่ใช่คุณรันเอง\n"
    "- /session-list และคำถามว่า 'มีอะไรทำงานอยู่ / ไปถึงไหนแล้ว / ใครติด blocker' ตอบได้จาก "
    "list_terminals โดยตรง\n"
    "\n"
    f"ข้อความที่ขึ้นต้นด้วย {DIGEST_TURN_MARKER} (task-67ba0c4f): นี่ไม่ใช่ CEO พิมพ์มาเอง "
    "แต่เป็นระบบอัตโนมัติที่ส่งจดหมายตอบจาก C-level (ที่ปิดงานด้วย report_to_ceo) มาให้คุณสรุปให้ CEO "
    "ฟัง กฎของ turn นี้ ห้ามฝ่าฝืนแม้แต่ข้อเดียว:\n"
    "1. สรุปด้วยคำพูดของคุณเอง เป็นภาษาไทย สั้นพอให้อ่านจากมือถือได้ ขึ้นต้นด้วยสิ่งที่ CEO สนใจที่สุดก่อน: "
    "เสร็จ/ไม่เสร็จ/ติด blocker และใครเป็นคนรายงาน\n"
    "2. ห้าม relay, ห้าม spawn, ห้ามเปิด terminal ใดๆ ใน turn นี้เด็ดขาด เพราะ turn นี้ไม่ได้เกิดจาก CEO "
    "สั่ง (กฎข้อ 2 ของกฎสำคัญด้านบนบอกไว้แล้วว่าทำสิ่งพวกนี้ได้เฉพาะตอน CEO สั่งเท่านั้น) turn สรุปงานที่ดัน "
    "ออกคำสั่งใหม่เองคือ loop ที่มีบิลค่าใช้จ่ายแนบมาด้วย ถ้ามีอะไรที่ดูเหมือนต้องสั่งต่อ ให้บอก CEO ว่าเห็น "
    "อะไร แล้วรอ CEO สั่งเองในข้อความถัดไป\n"
    "3. ห้ามเดาหรือแต่งสถานะ ถ้าจดหมายบอกว่า blocked ให้บอกว่า blocked พร้อมเหตุผลที่ C-level ให้มาตรงๆ "
    "ห้ามเบาลงเป็น 'กำลังทำอยู่'\n"
    "4. ต้องระบุแหล่งที่มาให้ชัดว่านี่คือรายงานที่เลขาส่งต่อมา ไม่ใช่ C-level พูดกับ CEO ตรงๆ (กฎเดียวกับ "
    "read_session ข้างบน)\n"
    "\n"
    "คุณไม่มี Bash และรันคำสั่งเชลล์ใดๆ ไม่ได้เลย ความสามารถของคุณมีแค่เครื่องมือที่ระบุไว้ทั้งหมดนี้ "
    "(LungNote อ่าน/เขียน, mac_status, org_snapshot, relay_to_session, spawn_c_level, read_session, "
    "list_terminals, session_history, open_terminal) "
    "ห้ามบอก CEO ว่าคุณรันคำสั่งเชลล์หรือทำสิ่งที่ไม่มี tool รองรับได้ "
    "ถ้า CEO ขอสิ่งที่ไม่มี tool รองรับ ให้บอกตรงๆ ว่าทำไม่ได้ "
    "ห้ามอ้างว่าทำได้แล้วค่อยปฏิเสธทีหลังตอนถูกขอจริง\n"
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
            },
            # task-b293ef6c Deliverable 4 — the secretary's four named proxy
            # actions (mac_status/org_snapshot/relay_to_session/
            # spawn_c_level). ROOT-relative, unlike the Mac-only literal
            # paths above/below, so this resolves correctly whether ROOT is
            # the Mac checkout or Contabo's /opt/mooniex-agents.
            # Launched by absolute file path, NOT `-m` plus `cwd`. Claude Code
            # silently drops an mcpServers entry that carries a `cwd` key: the
            # server still starts by hand, `initialize` and `tools/list` both
            # answer correctly, and yet the tools never reach the session —
            # nothing is logged on either side. Verified on Contabo by running
            # the identical config minus `cwd`, where they appear immediately.
            # The module puts its own repo root on sys.path from __file__, so
            # it does not need a working directory.
            "relay": {
                "type": "stdio",
                "command": str(ROOT / ".venv" / "bin" / "python"),
                "args": [str(ROOT / "runners" / "relay_mcp_server.py")],
                "env": {"PYTHONUNBUFFERED": "1"},
            },
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

def _bare_is_safe(env: dict[str, str] | None = None) -> bool:
    """Whether `--bare` can be used with this process's auth method.

    `env` is the ACTUAL env the subprocess will run with (defaults to
    `os.environ` when omitted, e.g. from a direct test call). This must be
    the resolved per-turn env, not the parent process's env, once D2
    (task-870f70f8) can switch provider between turns -- otherwise the
    provider changes but the OAuth-vs-token heuristic below keeps judging
    the OLD env, and `--bare` can go stale in the same turn it should have
    flipped (an OAuth turn that keeps `--bare` fails outright).

    `--bare` skips hooks, LSP and plugin discovery — a real latency win
    (measured on Contabo, same prompt with a tool call, 2 runs each:
    8.3-10.7s with vs 15.6-17.4s without). It ALSO skips reading
    ~/.claude/.credentials.json, so it only works when auth arrives through
    the environment.

    The comment that used to sit here concluded "--bare restricting auth to
    ANTHROPIC_API_KEY was the documented risk; it did not materialise". That
    conclusion came from testing the Z.ai path only, which authenticates via
    ANTHROPIC_AUTH_TOKEN and so could never have exposed the problem. The
    risk was real. Proven by A/B on Contabo 2026-08-14, the moment the
    secretary was switched to the Claude OAuth subscription:

        with    --bare -> is_error=true,  "Not logged in · Please run /login"
        without --bare -> is_error=false, "OK"

    So the flag is derived from the auth method instead of hardcoded: an env
    token (Z.ai, or any ANTHROPIC_API_KEY setup) keeps the fast path, while
    OAuth credential-file auth pays the extra ~7s rather than failing
    outright. SECRETARY_BARE=on|off forces it either way.
    """
    if env is None:
        env = os.environ
    override = (env.get("SECRETARY_BARE") or "").strip().lower()
    if override in ("on", "1", "true", "yes"):
        return True
    if override in ("off", "0", "false", "no"):
        return False
    return bool(env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY"))


def _resolve_provider_env() -> tuple[dict[str, str], str]:
    """Resolve which provider THIS turn should use, fresh every call, via
    lib.quota_router.pick_provider (GH mooniex-agents#38 D2, task-870f70f8)
    — instead of trusting whatever ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN
    / ANTHROPIC_MODEL happen to be pinned in /home/secretary/.secretary.env
    at service-start time. Both failure directions have hit for real, hours
    apart: pinned to Z.ai while its window was exhausted and Claude sat
    idle, then pinned to Claude while its OAuth credential was expired and
    Z.ai's window had long since reset.

    Returns (env, reason): env is a NEW dict built on top of a full copy of
    os.environ (nothing outside the 3 provider keys is touched, so this
    stays a computed override on top of the inherited env, not a filtered
    one) with those 3 keys either set (zai) or cleared (claude, so a stale
    Z.ai pin from the service file cannot win); reason is a one-line note
    for the info-level log the caller writes once per turn.

    Never blocks the turn: pick_provider reaches out over SSH and HTTP, so
    it runs on a background thread bounded by SECRETARY_QUOTA_TIMEOUT_SECONDS.
    Raising, timing out, or landing on a provider this file doesn't know how
    to build env for all fall back to the inherited env unchanged — a
    secretary that cannot answer because it could not measure quota is worse
    than one on a suboptimal provider.
    """
    # Everything below is one try/except on purpose: a raise from the dotenv
    # fallback reads (disk/permission hiccup) must fail safe exactly like a
    # raise from pick_provider itself -- both are "the quota check didn't
    # work", and both must fall through to the inherited env, not propagate
    # and turn into a hard failure of the whole turn.
    base_env = dict(os.environ)
    try:
        zai_usage_token = os.environ.get("ZAI_USAGE_TOKEN") or _read_dotenv_var("ZAI_USAGE_TOKEN")

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(pick_provider, zai_usage_token)
            provider = future.result(timeout=SECRETARY_QUOTA_TIMEOUT_SECONDS)
        finally:
            executor.shutdown(wait=False)

        if provider == "zai":
            key = (os.environ.get(_PROVIDER_KEY_VAR["zai"])
                   or _read_dotenv_var(_PROVIDER_KEY_VAR["zai"]))
            if not key:
                return base_env, "quota picked zai but no ZAI_API_KEY on this box — kept inherited env"
            env = dict(base_env)
            env["ANTHROPIC_BASE_URL"] = _PROVIDER_ENDPOINTS["zai"]
            env["ANTHROPIC_AUTH_TOKEN"] = key
            env["ANTHROPIC_MODEL"] = _PROVIDER_DEFAULT_MODEL["zai"]
            return env, "quota picked zai (more headroom)"

        if provider == "claude":
            env = dict(base_env)
            env.pop("ANTHROPIC_BASE_URL", None)
            env.pop("ANTHROPIC_AUTH_TOKEN", None)
            env.pop("ANTHROPIC_MODEL", None)
            return env, "quota picked claude (more headroom)"

        return base_env, f"quota check returned unrecognised provider {provider!r} — kept inherited env"
    except Exception as exc:
        return base_env, f"quota check unavailable ({exc!r}) — kept inherited env"


def _build_claude_cmd(prompt: str, session_id: str | None,
                       env: dict[str, str] | None = None) -> list[str]:
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--output-format", "json",
        "--permission-mode", "dontAsk",
    ]
    if _bare_is_safe(env):
        cmd.append("--bare")
    cmd += [
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

    cwd is always SECRETARY_WORKDIR — never caller-controlled. The base env
    is still inherited (not copied/filtered) on purpose — see
    _resolve_provider_env, which builds a full copy of os.environ and only
    ever touches the 3 provider-selection keys on top of it, once per call,
    logged at info level so a reviewer can answer "which provider did this
    turn use, and why" from the log.
    """
    env, reason = _resolve_provider_env()
    _log().info("secretary: provider for this turn — %s", reason)
    proc = subprocess.Popen(
        _build_claude_cmd(prompt, session_id, env),
        cwd=SECRETARY_WORKDIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,  # own process group, so a timeout can kill the whole tree
        env=env,
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


def _extract_api_error(stdout: str) -> str | None:
    """If `stdout` is a claude CLI JSON result for a FAILED run carrying a
    usable failure explanation, return it; else None. The caller only ever
    invokes this after rc != 0 — that is what makes it safe to trust
    `result` here at all (see below).

    Verified live 2026-08-14: a Z.ai Coding Plan 5h-quota rejection produces
    exit code 1, EMPTY stderr, and a normal-looking JSON body on stdout with
    `api_error_status: 429` and a `result` string that already names the
    reset time ("Usage limit reached for 5 hour. Your limit will reset at
    ..."). Nothing before this check inspected stdout when rc != 0, so this
    always fell through to the generic "exit code ผิดปกติ" message -- true,
    but useless, since the CLI had already told us exactly what happened.

    Widened 2026-08-15 (task-870f70f8): an OAuth-expired turn slipped past
    the check above because its `api_error_status` was null --

        {"is_error": true, "api_error_status": null,
         "terminal_reason": "api_error",
         "result": "Failed to authenticate: OAuth session expired and "
                    "could not be refreshed"}

    -- even though `terminal_reason` and `result` both said exactly what
    happened. `api_error_status` / `terminal_reason` are signals that a
    reason exists, not the only shape one can take, so this now trusts
    `result` itself whenever it is present and non-empty, on any failed
    run, regardless of which (if any) of those two fields are set. This is
    only safe BECAUSE the caller gates every call on rc != 0 first: a
    successful run also has a `result` (the actual answer), but rc == 0
    short-circuits before this function is ever called, so a good answer
    can never be turned into an error string here.

    `result` is model-adjacent text and goes straight to Telegram, so it is
    capped at API_ERROR_MAX_CHARS -- a runaway multi-KB blob must not
    become the CEO's entire error message.
    """
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    result = str(data.get("result") or "").strip()
    if not result:
        return None
    return result[:API_ERROR_MAX_CHARS]


def run_secretary_turn(prompt: str, conversation_id: str) -> str:
    """Run one turn for conversation_id. Never raises — every failure mode
    (bad exit code, unparseable output, timeout, stale --resume, upstream API
    error) becomes a friendly Thai error string instead of a 5xx or a hang
    (deliverable 2).
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

    # An upstream API error (rate limit, outage) is checked BEFORE the
    # stale-resume fallback below, and short-circuits it: retrying with a
    # fresh session cannot help a rate limit, which is per-account, not
    # per-session id -- without this check, one rate-limited message doubles
    # its own wall-clock cost (a doomed resume attempt, then a doomed fresh
    # retry) before surfacing a generic error that hides the real, already-
    # known reason and reset time.
    if rc != 0:
        api_error = _extract_api_error(stdout)
        if api_error:
            logger.error("secretary: upstream API error (conversation=%s): %s",
                         conversation_id, api_error[:300])
            return _friendly_error(f"โมเดลขัดข้องชั่วคราว — {api_error}")

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
            api_error = _extract_api_error(stdout)
            if api_error:
                logger.error("secretary: upstream API error on retry (conversation=%s): %s",
                             conversation_id, api_error[:300])
                return _friendly_error(f"โมเดลขัดข้องชั่วคราว — {api_error}")

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
