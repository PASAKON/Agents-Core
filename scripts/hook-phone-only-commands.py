#!/usr/bin/env python3
"""Stop hook: refuse a reply that hands the CEO a `!` command.

CEO ruling 2026-09-26: "ส่งคำสั่งมาที่ terminal.mooniex.com/run ... เขียน Skill
บังคับใช้ได้เลย ... เพราะฉะนั้นจะรัน command ผ่านมือถือเท่านั้น". The CEO runs
commands from the phone only, so a `! <command>` line in chat is a step nobody
can take. Commands go as Run Inbox cards (skill CXO_Run_Inbox, Rule 0).

Reads the transcript, takes every assistant text block written since the last
real user message (tool results do not count as a user message), and looks for
a `!` command: a `!` line inside a fenced code block, an inline `` `! cmd` ``, or
a plain line starting with `! <command>`. When it finds one it prints
{"decision": "block", "reason": ...} so the model rewrites the reply.

Never blocks twice in a row (`stop_hook_active`), and `PHONE_ONLY_GUARD=off`
turns it off for repairing this hook. A transcript it cannot read fails open
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

REASON = (
    "Phone-only rule (CEO 2026-09-26, skill CXO_Run_Inbox Rule 0): your reply hands the CEO a "
    "`!` command: {hit!r}. The CEO runs commands from the phone only. Send your correction "
    "without any `!` command. On contabo, create a Run Inbox card (tools/ask_run.py create, or "
    "MCP ask_run) and give its id and the /run link. On the Mac or winbox there is no card "
    "until P2. If only your own classifier blocked an action the CEO already ordered, ask him "
    "for one approval sentence in chat that names the target. Otherwise say 'card impossible "
    "on <host> until P2' and park it to LungNote."
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


def turn_text(transcript: Path) -> str:
    """Assistant text written since the last real user message."""
    parts: list[str] = []
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
                parts = []
            elif kind == "assistant":
                t = _text((rec.get("message") or {}).get("content"))
                if t.strip():
                    parts.append(t)
    return "\n".join(parts)


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


def decide(payload: dict, env=os.environ) -> dict | None:
    if env.get("PHONE_ONLY_GUARD", "").lower() == "off":
        return None
    if payload.get("stop_hook_active"):
        return None
    tp = payload.get("transcript_path")
    if not tp or not Path(tp).exists():
        return None
    hits = offenders(turn_text(Path(tp)))
    if not hits:
        return None
    return {"decision": "block", "reason": REASON.format(hit=hits[0][:160])}


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
