#!/usr/bin/env python3
"""session_merge.py — carry session A's context into session B, mark A merged.

Backs the /session-merge skill (`.claude/skills/session-merge/SKILL.md`).
This script does file-based extraction + one state write only. It does NOT
talk to LungNote (no MCP access from a bash-invoked script) and does NOT
synthesize the done/doing/blocked/left recap — that's the calling skill's
job, using the structured JSON this script prints as raw material.

Usage:
  python3 scripts/session_merge.py <role>                       # A_id omitted:
                                                                  # list not-yet-closed
                                                                  # candidates (shells out
                                                                  # to session_list.py) and exit
  python3 scripts/session_merge.py <role> <A_id> [B_id] --dry-run   # preview, no mutation
  python3 scripts/session_merge.py <role> <A_id> [B_id] --yes       # apply — writes A's .title

B_id defaults to $CXO_SESSION_ID / $CTO_SESSION_ID (the session this script
is run from) when omitted — the normal case is "merge A into ME".

Guard: refuses if A is currently live in an iTerm tab (partial-log read
risk) — reuses session_list.py's live_ids(), does not reimplement iTerm
querying. Only ever writes state/tab-titles/<role>-<A_id>.title; A's .log,
.base, and session-data files are never touched (audit trail stays intact).
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

from session_list import live_ids

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB_DIR = os.path.join(REPO, "state", "tab-titles")
LOG_DIR = os.path.join(REPO, "state", "logs")
SESSION_DATA_DIR = os.path.expanduser("~/.claude/session-data")

MAX_TITLE = 60
SECTION_RE = re.compile(r"^### (.+)$")


def build_title(base, summary):
    """Same truncation logic as scripts/tab-title.sh's python heredoc."""
    summary = " ".join(summary.split())
    title = f"{base} {summary}"
    if len(title) > MAX_TITLE:
        title = title[: MAX_TITLE - 1] + "…"
    return title


def list_candidates():
    script = os.path.join(REPO, "scripts", "session_list.py")
    r = subprocess.run([sys.executable, script], capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.stderr:
        sys.stderr.write(r.stderr)


def parse_session_summary(text):
    """Pull Tasks / Files Modified / Notes-for-next bullets out of a
    session-data .tmp file's '## Session Summary' block."""
    if "## Session Summary" not in text:
        return None
    body = text.split("## Session Summary", 1)[1]
    sections = {}
    current = None
    for line in body.splitlines():
        m = SECTION_RE.match(line.strip())
        if m:
            current = m.group(1).strip()
            sections[current] = []
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("<!--") or not stripped.startswith("- "):
            continue
        item = stripped[2:].strip()
        if item:
            sections[current].append(item)

    def get(name):
        return sections.get(name, [])

    return {
        "tasks": get("Tasks"),
        "files_modified": get("Files Modified"),
        "notes_for_next": get("Notes for Next Session"),
    }


def find_session_data(a_id):
    pattern = os.path.join(SESSION_DATA_DIR, f"*-{a_id}-session.tmp")
    matches = glob.glob(pattern)
    if not matches:
        return None
    matches.sort(key=os.path.getmtime, reverse=True)
    return matches[0]


def tail_log(role, a_id, n=200):
    path = os.path.join(LOG_DIR, f"{role}-{a_id}.log")
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return None, None
    return path, "".join(lines[-n:])


def pull_context(role, a_id):
    sd_path = find_session_data(a_id)
    if sd_path:
        try:
            text = open(sd_path, encoding="utf-8").read()
        except OSError:
            text = ""
        parsed = parse_session_summary(text)
        if parsed is not None:
            return {"source": "session-data", "path": sd_path, **parsed}
    log_path, tail = tail_log(role, a_id)
    if log_path:
        return {"source": "log-tail", "path": log_path, "log_tail": tail}
    return {"source": "none", "path": None}


def read_base(role, a_id):
    base_file = os.path.join(TAB_DIR, f"{role}-{a_id}.base")
    if os.path.isfile(base_file):
        try:
            line = open(base_file, encoding="utf-8").readline().strip()
            if line:
                return line
        except OSError:
            pass
    return f"{role.upper()} #{a_id}"


def mark_merged(role, a_id, b_id, apply_write):
    title_file = os.path.join(TAB_DIR, f"{role}-{a_id}.title")
    before = None
    if os.path.isfile(title_file):
        try:
            before = open(title_file, encoding="utf-8").read().strip()
        except OSError:
            before = None
    base = read_base(role, a_id)
    after = build_title(base, f"🔗 merged→#{b_id}")
    written = False
    if apply_write:
        os.makedirs(TAB_DIR, exist_ok=True)
        with open(title_file, "w", encoding="utf-8") as f:
            f.write(after + "\n")
        written = True
    return {
        "path": title_file,
        "base": base,
        "before": before,
        "after": after,
        "written": written,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Merge session A's context into session B; mark A merged."
    )
    ap.add_argument("role")
    ap.add_argument("ids", nargs="*", help="[A_id] [B_id]")
    ap.add_argument("--yes", action="store_true",
                     help="pre-confirmed: allow the A.title mutation")
    ap.add_argument("--dry-run", "--list-only", dest="dry_run", action="store_true",
                     help="preview only (context pull + title-change preview), never mutate state")
    args = ap.parse_args()

    role = args.role.lower()
    a_id = args.ids[0].lower() if len(args.ids) >= 1 else None
    if len(args.ids) >= 2:
        b_id = args.ids[1].lower()
    else:
        b_id = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID")
        b_id = b_id.lower() if b_id else None

    if a_id is None:
        print("# no A_id given — not-yet-closed candidates "
              "(confirm one with the user, then re-run with an explicit id)\n")
        list_candidates()
        sys.exit(2)

    live, ok = live_ids()
    if not ok:
        print("⚠ iTerm query failed — cannot verify session A is idle; proceed with caution",
              file=sys.stderr)
    elif a_id in live:
        print(f"refuse: {role}-{a_id} is currently live in an iTerm tab — "
              f"close/idle session A first (partial-log read risk)", file=sys.stderr)
        sys.exit(1)

    if not b_id:
        print("error: B_id required (pass explicitly, or run inside a session with "
              "CXO_SESSION_ID / CTO_SESSION_ID set)", file=sys.stderr)
        sys.exit(2)

    result = {
        "role": role,
        "a_id": a_id,
        "b_id": b_id,
        "mode": "dry-run" if args.dry_run else "apply",
        "live_guard": {"checked": ok, "a_is_live": (a_id in live) if ok else None},
        "context": pull_context(role, a_id),
    }

    if args.dry_run:
        result["title_update"] = mark_merged(role, a_id, b_id, apply_write=False)
    else:
        if not args.yes:
            print("refuse: mutation requires --yes (get explicit user confirmation first) "
                  "or pass --dry-run to preview", file=sys.stderr)
            sys.exit(3)
        result["title_update"] = mark_merged(role, a_id, b_id, apply_write=True)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
