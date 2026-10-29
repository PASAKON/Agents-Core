#!/usr/bin/env python3
"""Stop hook: refuse a reply that hands the CEO a `!` command.

CEO ruling 2026-09-26: "ส่งคำสั่งมาที่ terminal.mooniex.com/run ... เขียน Skill
บังคับใช้ได้เลย ... เพราะฉะนั้นจะรัน command ผ่านมือถือเท่านั้น". The CEO runs
commands from the phone only, so a `! <command>` line in chat is a step nobody
can take. Commands go as Run Inbox cards (skill ALL_Protocol_RunInbox, Rule 0).

Reads the transcript, takes every assistant text block written since the last
real user message (tool results do not count as a user message), and looks for
a `!` command: a `!` line inside a fenced code block, an inline `` `! cmd` ``, or
a plain line starting with `! <command>`. When it finds one it prints
{"decision": "block", "reason": ...} so the model rewrites the reply.

Second check, `question_offenders()` (CEO 2026-10-30): a C-level or Project Head
(CXO_ROLE cto, cmo, cgo, cfo or project_head) that asks the CEO something in chat,
with no question card or blocker letter in the same turn, is blocked and told to
raise the card. A turn is exempt when it holds an ask_ceo / ask_run tool call, a
Bash `tools/ask_run.py ask|create` or `relay-request.mjs open`, a SendMessage or
send_to_cxo whose input says "blocker", or a card / request id in its text. Lines
inside code, `>` quotes and "..." quotes are not scanned. `CARD_GUARD=off` turns
only this check off.

Never blocks twice in a row (`stop_hook_active`), and `PHONE_ONLY_GUARD=off`
turns the whole hook off for repairing it. A transcript it cannot read fails open
with a line on stderr, so a broken hook never traps a session.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

FENCE = re.compile(r"^\s*(```|~~~)")
FENCED_BANG = re.compile(r"^\s*!\s*[A-Za-z0-9_./~$\"'-]")
INLINE_BANG = re.compile(r"`!\s*[A-Za-z0-9_./~$][^`\n]*`")
PLAIN_BANG = re.compile(r"^\s*!\s+[A-Za-z./~$]")

# lib/roles.py c_level_roles() minus coo (SomPong talks to the CEO on LINE and Telegram
# through its own tools) plus project_head. Hardcoded so the hook stays stdlib-only;
# tests/test_hook_phone_only_commands.py compares it with c_level_roles().
QUESTION_ROLES = frozenset({"cto", "cmo", "cgo", "cfo", "project_head"})
ASK_TOOLS = frozenset({"mcp__org__ask_ceo", "mcp__org__ask_run", "mcp__sompong__ask_ceo"})
LETTER_TOOLS = frozenset({"SendMessage", "mcp__org__send_to_cxo"})
# ask_run.py takes its verb first, so the verb sits right after the script name.
CARD_COMMAND = re.compile(
    r"(?:tools/ask_run\.py|tools\.ask_run)\s+(?:ask|create)\b|relay-request\.mjs\s+open\b")
BLOCKER = re.compile(r"\bblocker\b", re.IGNORECASE)
CARD_ID = re.compile(r"(?:Q|QG|RUN)-\d{8}-\d{4}-[0-9a-f]{4}|rq-[0-9a-f]{8}")
INLINE_CODE = re.compile(r"`[^`\n]*`")
QUOTED = re.compile(r'"[^"\n]*"|\u201c[^\u201d\n]*\u201d')
ENDS_WITH_QUESTION = re.compile(r"[?？]\s*$")
ADDRESSES_CEO = re.compile(r"คุณ|ท่าน|\byou\b|\byour\b", re.IGNORECASE)
ASKS = [re.compile(p, re.IGNORECASE) for p in (
    # Thai
    r"(ไหม|มั้ย|มั๊ย|หรือเปล่า|รึเปล่า|หรือไม่|หรือยัง)\s*(ครับ|คะ|ค่ะ|คับ)",
    r"(ไหม|มั้ย|มั๊ย|หรือเปล่า|รึเปล่า)\s*[?？]",
    r"(ไหน|อะไร|ยังไง|อย่างไร|เมื่อไหร่|เมื่อไร)\s*(ดี)?\s*(ครับ|คะ|ค่ะ)\s*[?？]?\s*$",
    r"(เลือก|ตอบ|พิมพ์|ยืนยัน|อนุมัติ)[^\n]{0,40}?(ได้เลย|ด้วย|หน่อย)\s*(ครับ|คะ|ค่ะ|นะครับ|นะคะ)",
    r"รอ\s*(คำตอบ|คำยืนยัน|การตัดสินใจ)\s*(จาก)?\s*(คุณ|ท่าน|CEO)",
    # English
    r"\b(should|shall|can|may) I\b[^\n]{0,80}\?",
    r"\bwant me to\b",
    r"\b(do|would) you (want|like|prefer)\b",
    r"\b(just )?reply (with|yes|no)\b",
    r"\blet me know\b",
    r"\bplease (confirm|approve|choose|pick|decide|reply|answer)\b",
    r"\b(which|what) (one|option|account|version)\b[^\n]{0,60}\?",
    r"\byour (call|decision|choice|go-ahead|approval)\b",
    r"\b(ok|okay) to\b[^\n]{0,60}\?",
)]

REASON = (
    "Phone-only rule (CEO 2026-09-26, skill ALL_Protocol_RunInbox Rule 0): your reply hands the CEO a "
    "`!` command: {hit!r}. The CEO runs commands from the phone only. Send your correction "
    "without any `!` command. On contabo, create a Run Inbox card (tools/ask_run.py create, or "
    "MCP ask_run) and give its id and the /run link. On the Mac or winbox there is no card "
    "until P2. If only your own classifier blocked an action the CEO already ordered, ask him "
    "for one approval sentence in chat that names the target. Otherwise say 'card impossible "
    "on <host> until P2' and park it to LungNote."
)
QUESTION_REASON = (
    "Run-card rule (CEO 30 Oct 2026, every C-level and PH): your reply asks the CEO something in "
    "chat: {hit!r}. If it is his to decide (money, secrets, permanent deletion, speaking in his "
    "name, his accounts or devices, or a choice he asked to make), raise a question card now "
    "(mcp__org__ask_ceo, or tools/ask_run.py ask; on winbox or the Mac send one blocker letter to "
    "your Contabo C-level) and end with the card id. If it is yours to decide, decide and say what "
    "you chose. If the line is not a question to the CEO, end without changing anything."
)


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text") or ""
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _is_real_user(msg) -> bool:
    content = (msg or {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") == "text" for b in content)
    return False


def turn(transcript: Path) -> tuple[str, list[dict]]:
    """Assistant text and tool_use blocks written since the last real user message."""
    parts: list[str] = []
    tools: list[dict] = []
    with transcript.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = rec.get("type")
            if kind == "user" and _is_real_user(rec.get("message")):
                parts, tools = [], []
            elif kind == "assistant":
                content = (rec.get("message") or {}).get("content")
                t = _text(content)
                if t.strip():
                    parts.append(t)
                if isinstance(content, list):
                    tools.extend(b for b in content
                                 if isinstance(b, dict) and b.get("type") == "tool_use")
    return "\n".join(parts), tools


def turn_text(transcript: Path) -> str:
    """Assistant text written since the last real user message."""
    return turn(transcript)[0]


def offenders(text: str) -> list[str]:
    hits: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            if FENCED_BANG.match(line):
                hits.append(line.strip())
            continue
        if PLAIN_BANG.match(line):
            hits.append(line.strip())
        hits.extend(m.group(0) for m in INLINE_BANG.finditer(line))
    return hits


def _raises_card(text: str, tools: list[dict]) -> bool:
    """True when the turn already put its question where the CEO answers it: a card
    tool or command, a blocker letter to a Contabo C-level, or a card id in the text."""
    if CARD_ID.search(text):
        return True
    for t in tools:
        name = t.get("name")
        inp = t.get("input")
        if name in ASK_TOOLS:
            return True
        if name == "Bash" and isinstance(inp, dict) and CARD_COMMAND.search(str(inp.get("command") or "")):
            return True
        if name in LETTER_TOOLS and BLOCKER.search(json.dumps(inp, ensure_ascii=False)):
            return True
    return False


def question_offenders(text: str, tools: list[dict]) -> list[str]:
    """Lines of the turn that ask the CEO something in chat, when the turn raised no
    card. Fenced code, `>` lines, inline code and quoted words are not scanned."""
    if _raises_card(text, tools):
        return []
    hits: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or line.lstrip().startswith(">"):
            continue
        bare = QUOTED.sub(" ", INLINE_CODE.sub(" ", line))
        if any(rx.search(bare) for rx in ASKS) or (
                ENDS_WITH_QUESTION.search(bare) and ADDRESSES_CEO.search(bare)):
            hits.append(line.strip())
    return hits


def decide(payload: dict, env=os.environ) -> dict | None:
    if env.get("PHONE_ONLY_GUARD", "").lower() == "off":
        return None
    if payload.get("stop_hook_active"):
        return None
    tp = payload.get("transcript_path")
    if not tp or not Path(tp).exists():
        return None
    text, tools = turn(Path(tp))
    reasons = [REASON.format(hit=h[:160]) for h in offenders(text)[:1]]
    if env.get("CXO_ROLE", "") in QUESTION_ROLES and env.get("CARD_GUARD", "").lower() != "off":
        try:
            reasons += [QUESTION_REASON.format(hit=h[:160]) for h in question_offenders(text, tools)[:1]]
        except Exception as e:  # a bug here must not take the `!` check down with it
            print(f"hook-phone-only-commands: question check failed, skipped ({e})", file=sys.stderr)
    if not reasons:
        return None
    return {"decision": "block", "reason": "\n\n".join(reasons)}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"hook-phone-only-commands: bad payload, not checking ({e})", file=sys.stderr)
        return 0
    try:
        out = decide(payload)
    except OSError as e:
        print(f"hook-phone-only-commands: transcript unreadable, not checking ({e})", file=sys.stderr)
        return 0
    if out:
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
