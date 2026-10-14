#!/usr/bin/env python3
"""PH code-write telemetry. Never blocks; never records shell commands."""
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
EXTS = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".sh", ".ps1", ".go", ".rs", ".sql"}


def shell_ext(command):
    tokens = shlex.split(command, posix=True)
    if re.search(r"\bgit\s+(?:-[^;|&]+\s+)?commit\b", command):
        return ""
    # Redirections, including attached destinations and heredoc output paths.
    targets = re.findall(r">>?\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s;&|<>]+))", command)
    paths = [next(v for v in group if v) for group in targets]
    if re.search(r"\bsed\s+[^;|&]*?(?:-i\b|--in-place\b)", command) or "tee" in tokens:
        paths.extend(tokens)
    for path in paths:
        ext = Path(path).suffix.lower()
        if ext in EXTS:
            return ext
    return None


def main():
    if os.environ.get("CXO_ROLE") != "project_head":
        return 0
    try:
        payload = json.load(sys.stdin)
        tool = payload.get("tool_name")
        inp = payload.get("tool_input", {})
        path = inp.get("file_path") or inp.get("notebook_path") or ""
        ext = Path(path).suffix.lower()
        if tool == "Bash":
            path, ext = "shell", shell_ext(inp.get("command", ""))
            if ext is None:
                return 0
        elif tool not in {"Edit", "Write", "NotebookEdit"} or ext not in EXTS:
            return 0
        now = datetime.now(timezone.utc)
        sid = payload.get("session_id", "")
        spool = Path(os.environ.get("PH_HANDSON_PATH", ROOT / "state/reports/ph-handson.jsonl"))
        spool.parent.mkdir(parents=True, exist_ok=True)
        # Lock the spool so simultaneous tools cannot both emit a reminder.
        with spool.open("a+", encoding="utf-8") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0)
            remind = bool(sid)
            for line in stream:
                try:
                    row = json.loads(line)
                    if row.get("session_id") == sid and row.get("reminded") and (
                        now - datetime.fromisoformat(row["ts"])).total_seconds() < 1800:
                        remind = False
                except (ValueError, TypeError, KeyError):
                    continue
            stream.write(json.dumps(dict(ts=now.isoformat(), session_id=sid, tool=tool,
                                         path=path, ext=ext, reminded=remind)) + "\n")
        if remind:
            print(json.dumps({"systemMessage": "PH = lead only, delegate code with delegate_task."}))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
