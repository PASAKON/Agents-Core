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
MAX_COMMAND = 4096  # a Bash command is cut here before any regex or shlex: their cost grows with length
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?[ \t]*(['\"]?)([A-Za-z_]\w*)\1")
SEPARATOR = re.compile(r"&&|[;|]")
GIT = re.compile(r"\bgit\b")
COMMIT = re.compile(r"\bcommit\b")
REDIRECT = re.compile(r">>?\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s;&|<>]+))")
IN_PLACE = re.compile(r"-(?!-)[A-Za-z]*i|--in-place")


def segments(command):
    """Command segments of the first MAX_COMMAND chars; heredoc bodies are content, not commands."""
    waiting = []  # heredoc delimiters whose body has not ended yet
    for line in command[:MAX_COMMAND].split("\n"):
        if waiting:
            if line.strip() == waiting[0]:
                waiting.pop(0)
            continue
        waiting = [m.group(2) for m in HEREDOC.finditer(line)]
        yield from SEPARATOR.split(line)


def shell_ext(command):
    for segment in segments(command):
        git = GIT.search(segment)
        if git and COMMIT.search(segment, git.end()):
            continue  # this segment is a git commit; the others still count
        try:
            tokens = shlex.split(segment, posix=True)
        except ValueError:  # e.g. an unbalanced quote
            tokens = segment.split()
        # Redirections, including attached destinations and heredoc output paths.
        paths = [next(v for v in group if v) for group in REDIRECT.findall(segment)]
        if "tee" in tokens or ("sed" in tokens and any(IN_PLACE.match(t) for t in tokens)):
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
        with spool.open("a+b") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0, os.SEEK_END)
            start = max(0, stream.tell() - 64 * 1024)
            stream.seek(start)
            tail = stream.read(64 * 1024)
            if start:
                # The first record may be truncated, including inside UTF-8.
                tail = tail.partition(b"\n")[2]
            remind = bool(sid)
            for line in tail.splitlines():
                try:
                    row = json.loads(line)
                    if row.get("session_id") == sid and row.get("reminded") and (
                        now - datetime.fromisoformat(row["ts"])).total_seconds() < 1800:
                        remind = False
                except (ValueError, TypeError, KeyError):
                    continue
            stream.write(json.dumps(dict(ts=now.isoformat(), session_id=sid, tool=tool,
                                         path=path, ext=ext, reminded=remind)).encode("utf-8") + b"\n")
        if remind:
            print(json.dumps({"systemMessage": "PH = lead only, delegate code with delegate_task."}))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
