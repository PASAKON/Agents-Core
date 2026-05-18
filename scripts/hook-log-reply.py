#!/usr/bin/env python3
"""Stop hook: append last assistant reply to state/logs/cto.log.

Reads transcript_path (jsonl) from hook event JSON, finds last
assistant message, concatenates text-typed content blocks, writes
a timestamped line.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "state" / "logs" / "cto.log"
MAX_CHARS = 4000


def extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text") or ""
                if t:
                    parts.append(t)
        return "\n".join(parts)
    return ""


def main() -> int:
    if os.environ.get("CTO_SESSION") != "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tp = payload.get("transcript_path")
    if not tp:
        return 0
    p = Path(tp)
    if not p.exists():
        return 0

    last_text = ""
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("type") != "assistant":
                    continue
                msg = rec.get("message") or {}
                text = extract_text(msg.get("content"))
                if text.strip():
                    last_text = text
    except Exception:
        return 0

    last_text = last_text.strip()
    if not last_text:
        return 0
    if len(last_text) > MAX_CHARS:
        last_text = last_text[:MAX_CHARS] + " ...[truncated]"

    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{ts}] CTO: {last_text}\n"
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
