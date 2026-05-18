#!/usr/bin/env python3
"""UserPromptSubmit hook for CTO sessions.

Two responsibilities:
  1. Append the CEO prompt to state/logs/cto.log with a `CEO:` prefix.
  2. Surface any new `Dev:*` lines (or CTO-event lines) that arrived in
     cto.log since the previous hook fire as additional context, so the
     CTO model sees DEV progress inline in its next reasoning step.

State for #2: byte offset stored at state/.cto_log_pos.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "state" / "logs" / "cto.log"
STATE = ROOT / "state" / ".cto_log_pos"

DEV_PREFIX = "] Dev:"
EVENT_PREFIX = "] CTO-event"
MAX_LINES = 50


def _read_offset() -> int:
    try:
        return int(STATE.read_text().strip())
    except (OSError, ValueError):
        return 0


def _write_offset(n: int) -> None:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(str(n))
    except OSError:
        pass


def _pending_lines(offset: int) -> list[str]:
    if not LOG.exists():
        return []
    try:
        size = LOG.stat().st_size
    except OSError:
        return []
    if offset > size:
        offset = 0
    with LOG.open("rb") as f:
        f.seek(offset)
        data = f.read()
    text = data.decode("utf-8", errors="replace")
    return [l for l in text.splitlines() if l.strip()]


def main() -> int:
    if os.environ.get("CTO_SESSION") != "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return 0

    offset_before = _read_offset()
    pending = _pending_lines(offset_before)
    surfaced = [l for l in pending if DEV_PREFIX in l or EVENT_PREFIX in l]
    if len(surfaced) > MAX_LINES:
        surfaced = surfaced[-MAX_LINES:]

    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] CEO: {prompt}\n")

    try:
        _write_offset(LOG.stat().st_size)
    except OSError:
        pass

    if surfaced:
        print("## Recent DEV / org activity (since your previous reply)")
        print()
        for line in surfaced:
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
