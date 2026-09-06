#!/usr/bin/env python3
"""PreToolUse hook — no Google Drive action before the `gdrive-filing` skill is read.

CEO 2026-09-06: "ถ้าจะใช้งาน Gdrive อ่าน Skills นี้ก่อนเสมอ มันเป็นกฏ". The skill holds
the folder map, the IDs and the ask-first rules; a session that has not read it
files things at the Drive root (which is exactly what happened that morning).
Prose does not stop that. This does.

Arms (creates ~/.gateguard/gdrive-skill-<session>.ok) when the session reads the
skill: the Skill tool with `gdrive-filing`, a Read of its SKILL.md, or a Bash
command that opens the SKILL.md. Stays armed 12 hours, then re-arms — the rules
change and a stale reading is no reading.

Blocks (exit 2, message to the model) any Drive-touching call while unarmed:
  - every `mcp__claude_ai_Google_Drive__*` tool
  - Bash commands mentioning rclone, the gdrive-bridge CLI, the synced Drive
    folder (GoogleDrive-… / ไดรฟ์ของฉัน) or an `gdrive:` remote — including
    commands that only carry them inside a winrun snippet.

Escape hatch, for genuine repair only: GDRIVE_GATE=off.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

SKILL_FILE = "gdrive-filing/SKILL.md"
ARMED_FOR_S = 12 * 3600
DRIVE_RE = re.compile(
    r"\brclone\b|gdrive_move\.py|gdrive-bridge|GoogleDrive-|ไดรฟ์ของฉัน|CloudStorage/GoogleDrive|\bgdrive:",
    re.IGNORECASE,
)


def main() -> int:
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    if os.environ.get("GDRIVE_GATE", "").strip().lower() == "off":
        return 0
    sid = str(ev.get("session_id") or "nosession")
    tool = str(ev.get("tool_name") or "")
    inp = ev.get("tool_input") or {}
    marker = Path.home() / ".gateguard" / f"gdrive-skill-{sid}.ok"

    # Reading the skill arms the gate.
    read = (
        (tool == "Skill" and str(inp.get("skill", "")).endswith("gdrive-filing"))
        or (tool == "Read" and SKILL_FILE in str(inp.get("file_path", "")))
        or (tool == "Bash" and SKILL_FILE in str(inp.get("command", "")))
    )
    if read:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(time.time()))
        return 0

    touches_drive = tool.startswith("mcp__claude_ai_Google_Drive__") or (
        tool == "Bash" and bool(DRIVE_RE.search(str(inp.get("command", ""))))
    )
    if not touches_drive:
        return 0
    if marker.exists():
        try:
            armed_at = float(marker.read_text().strip() or 0)
        except ValueError:
            armed_at = 0.0
        if time.time() - armed_at < ARMED_FOR_S:
            return 0
    sys.stderr.write(
        "BLOCKED — Google Drive rule (CEO 2026-09-06): read the `gdrive-filing` skill "
        "before ANY Drive action in this session.\n\n"
        "This call touches Drive (rclone / gdrive-bridge / Drive MCP / the synced Drive folder) "
        "and the skill has not been read in the last 12 hours of this session.\n\n"
        "Do this first: invoke the Skill tool with `gdrive-filing` (or Read "
        ".claude/skills/gdrive-filing/SKILL.md in the Agents repo). Then follow it: ask before "
        "creating/moving/deleting, file only into defined folders (else UNKNOWN), keep the tree "
        "and ID table in sync, and use the drive-archive-gate row for anything moved off a machine. "
        "Then retry this exact call.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
