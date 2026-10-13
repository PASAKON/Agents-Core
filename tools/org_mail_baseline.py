#!/usr/bin/env python3
"""Baseline of org mail in context: what the mail hooks feed each session, per day.

Org restructure P0 (plan by SomPong, PH #3c1f65ae, 2026-10-13). Read only: it
parses the Claude Code transcripts that already exist and changes no hook, no
state file and no hub row. Its numbers are the "before" that envelope mail
(P1, `ORG_MAIL_ENVELOPE`) is measured against.

Per Thai calendar day and per session it reports:
  * characters that `scripts/hook-inbox.py` (mailbox drain) and
    `scripts/hook-log-prompt.py` (cto.log tail) put into context. A
    UserPromptSubmit hook's stdout is the context it adds; Claude Code records
    every non-empty one as an `attachment` of type `hook_success` carrying that
    stdout. An empty hook output leaves no record, so silence counts as 0.
  * wakes: prompt submissions (distinct `promptId`), split by what started them
    (`origin.kind` of the turn's first record, else its text).
  * average `cache_read_input_tokens` per wake: on the wake's first API call
    (what waking the session re-reads) and summed over the whole turn. Usage is
    kept once per assistant `message.id`; Claude Code writes the same message
    once per content block (see tools/token_profile.py).

Every number printed is MEASURED (counted from transcript records). Nothing
here is estimated; what the transcripts cannot show is listed as NOT MEASURED
under coverage instead of being guessed (e.g. a user's transcripts this
process cannot read, or another machine's).

Usage:
  python3 tools/org_mail_baseline.py                 # today + the 3 days before
  python3 tools/org_mail_baseline.py --days 7 --json
  python3 tools/org_mail_baseline.py --root ~/.claude/projects --root /x/projects
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import sys
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    THAI = ZoneInfo("Asia/Bangkok")
except Exception:  # no tz database on the box: Thailand has no DST
    THAI = dt.timezone(dt.timedelta(hours=7))

INBOX_HOOK = "hook-inbox.py"
LOG_HOOK = "hook-log-prompt.py"
WAKE_MARKER = "[New message from "           # tools/agent_transport._WAKE_MARKER_TEMPLATE
PEER_PREFIXES = ("Another Claude session sent a message", "<cross-session-message")
LETTERS_RE = re.compile(r"## Mailbox \S+ (\d+) letter")
TITLE_ROLE_RE = re.compile(r"\b(CTO|CMO|CFO|CGO|COO|PH|SomPong)\b")
WORKER_DIR_RE = re.compile(r"--([a-z][a-z_-]*)--(task-[0-9a-f]{6,})$")
WAKE_KINDS = ("human", "peer", "task", "mailbox", "launch", "other")
LAUNCH_PREFIXES = ("# Task task-",)            # a worker kickoff the launcher types
# substrings a line must hold to be worth json-parsing (most lines are not);
# no `"type":` prefix, so a writer that puts a space after the colon still matches
_KEEP = ('"user"', '"assistant"', '"hook_success"', '"custom-title"')


def default_roots() -> list[Path]:
    roots = [Path.home() / ".claude" / "projects"]
    cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    if cfg:
        roots.append(Path(cfg) / "projects")
    out: list[Path] = []
    for r in roots:
        if r not in out:
            out.append(r)
    return out


def _ts(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _text(content) -> str | None:
    """Prompt text of a user record, None for a tool_result record."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        return " ".join(b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text")
    return None


def wake_kind(rec: dict, text: str) -> str:
    origin = rec.get("origin")
    kind = origin.get("kind") if isinstance(origin, dict) else origin
    t = text.lstrip()
    if WAKE_MARKER in t[:200]:
        return "mailbox"
    if kind == "peer" or t.startswith(PEER_PREFIXES):
        return "peer"
    if kind == "task-notification" or t.startswith("<task-notification>"):
        return "task"
    if t.startswith(LAUNCH_PREFIXES):
        return "launch"
    if kind == "human":
        return "human"
    return "other"


def session_kind(title: str | None, project_dir: str, headless: bool = False) -> tuple[str, str]:
    """(kind, role): kind is 'worker', 'headless' (`claude -p`) or 'session'."""
    m = WORKER_DIR_RE.search(project_dir)
    if m:
        return "worker", m.group(1)
    if title:
        r = TITLE_ROLE_RE.search(title)
        if r:
            return "session", r.group(1)
    return ("headless" if headless else "session"), "?"


def _new_cell() -> dict:
    return {
        "wakes": collections.Counter(),
        "inbox_chars": 0, "inbox_fires": 0, "letters": 0,
        "log_chars": 0, "log_fires": 0, "log_lines": 0,
        "peer_chars": 0,
        "first_cr": [], "first_cw": [], "turn_cr": [],
    }


def scan_file(path: Path, start: dt.datetime, end: dt.datetime, cells: dict,
              meta: dict) -> None:
    """Add one transcript's records inside [start, end) to `cells`, keyed by
    (thai_date, session_id)."""
    project_dir = path.parent.name
    title = None
    seen_msg: set[str] = set()
    cur = None            # (cell, day) of the turn in progress, None outside the window
    cur_prompt = None
    turn_cr = 0
    first_cr = None
    first_cw = None
    sid = None
    headless = False

    def close_turn():
        nonlocal cur, turn_cr, first_cr, first_cw
        if cur is not None and first_cr is not None:
            cur["first_cr"].append(first_cr)
            cur["first_cw"].append(first_cw or 0)
            cur["turn_cr"].append(turn_cr)
        cur, turn_cr, first_cr, first_cw = None, 0, None, None

    with open(path, errors="replace") as fh:
        for line in fh:
            if not any(k in line for k in _KEEP):
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            sid = rec.get("sessionId") or sid
            headless = headless or str(rec.get("entrypoint") or "").startswith("sdk")
            typ = rec.get("type")
            if typ == "custom-title":
                title = rec.get("customTitle") or title
                continue
            if rec.get("isSidechain"):
                continue
            ts = _ts(rec.get("timestamp"))
            in_window = ts is not None and start <= ts < end
            day = ts.astimezone(THAI).date().isoformat() if ts else None
            key = (day, sid)

            if typ == "user":
                text = _text((rec.get("message") or {}).get("content"))
                pid = rec.get("promptId")
                if text is None or not pid or pid == cur_prompt:
                    continue
                if rec.get("isCompactSummary"):
                    cur_prompt = pid  # a compaction resumes the turn in progress; it wakes nobody
                    continue
                # a new prompt submission: one wake
                close_turn()
                cur_prompt = pid
                if not in_window:
                    continue
                cell = cells.setdefault(key, _new_cell())
                kind = wake_kind(rec, text)
                cell["wakes"][kind] += 1
                if kind == "peer":
                    cell["peer_chars"] += len(text)
                cur = cell
            elif typ == "assistant":
                msg = rec.get("message") or {}
                mid = msg.get("id")
                if not mid or mid in seen_msg:
                    continue
                seen_msg.add(mid)
                if cur is None:
                    continue
                usage = msg.get("usage") or {}
                cr = usage.get("cache_read_input_tokens") or 0
                if first_cr is None:
                    first_cr = cr
                    first_cw = usage.get("cache_creation_input_tokens") or 0
                turn_cr += cr
            elif typ == "attachment":
                att = rec.get("attachment")
                if not isinstance(att, dict) or att.get("type") != "hook_success" or not in_window:
                    continue
                cmd = att.get("command") or ""
                out = att.get("stdout")
                if not isinstance(out, str):
                    out = att.get("content") if isinstance(att.get("content"), str) else ""
                if not out:
                    continue
                if INBOX_HOOK in cmd:
                    cell = cells.setdefault(key, _new_cell())
                    cell["inbox_chars"] += len(out)
                    cell["inbox_fires"] += 1
                    m = LETTERS_RE.search(out)
                    cell["letters"] += int(m.group(1)) if m else 0
                elif LOG_HOOK in cmd:
                    cell = cells.setdefault(key, _new_cell())
                    cell["log_chars"] += len(out)
                    cell["log_fires"] += 1
                    cell["log_lines"] += sum(1 for l in out.splitlines()
                                             if l.strip() and not l.startswith("## "))
    close_turn()
    if sid:
        kind, role = session_kind(title, project_dir, headless)
        prev = meta.get(sid) or {}
        meta[sid] = {"title": title or prev.get("title") or project_dir,
                     "kind": kind, "role": role, "dir": project_dir}


def collect(roots: list[Path], days: int, today: dt.date | None = None) -> dict:
    today = today or dt.datetime.now(THAI).date()
    first_day = today - dt.timedelta(days=days - 1)
    start = dt.datetime.combine(first_day, dt.time(), THAI)
    end = dt.datetime.combine(today + dt.timedelta(days=1), dt.time(), THAI)
    cells: dict = {}
    meta: dict = {}
    scanned, unreadable, missing = [], [], []
    for root in roots:
        if not root.exists():
            missing.append(str(root))
            continue
        if not os.access(root, os.R_OK | os.X_OK):
            unreadable.append(str(root))
            continue
        for f in sorted(glob.glob(str(root / "*" / "*.jsonl"))):
            try:
                if dt.datetime.fromtimestamp(os.path.getmtime(f), dt.timezone.utc) < start:
                    continue      # last written before the window: nothing in it
                scan_file(Path(f), start, end, cells, meta)
                scanned.append(f)
            except OSError:
                unreadable.append(f)
    return {"days": [(first_day + dt.timedelta(days=i)).isoformat() for i in range(days)],
            "cells": cells, "meta": meta,
            "coverage": {"roots": [str(r) for r in roots], "files_scanned": len(scanned),
                         "missing_roots": missing, "unreadable": unreadable}}


def _avg(xs: list[int]) -> int | None:
    return round(sum(xs) / len(xs)) if xs else None


def rows(data: dict, include_headless: bool = False) -> list[dict]:
    """One row per (day, session). `claude -p` runs (measurement probes, eval
    calls) run no org hook and are left out unless asked for."""
    out = []
    for (day, sid), c in data["cells"].items():
        m = data["meta"].get(sid, {})
        if m.get("kind") == "headless" and not include_headless:
            continue
        out.append({
            "day": day, "session": (sid or "?")[-8:], "session_id": sid,
            "title": m.get("title"), "kind": m.get("kind"), "role": m.get("role"),
            "wakes": sum(c["wakes"].values()),
            **{f"wakes_{k}": c["wakes"].get(k, 0) for k in WAKE_KINDS},
            "inbox_chars": c["inbox_chars"], "inbox_fires": c["inbox_fires"],
            "letters": c["letters"],
            "ctolog_chars": c["log_chars"], "ctolog_fires": c["log_fires"],
            "ctolog_lines": c["log_lines"],
            "peer_msg_chars": c["peer_chars"],
            "cache_read_first_call_avg": _avg(c["first_cr"]),
            "cache_write_first_call_avg": _avg(c["first_cw"]),
            "cache_read_per_wake_avg": _avg(c["turn_cr"]),
            "turns_with_usage": len(c["turn_cr"]),
        })
    out.sort(key=lambda r: (r["day"], -(r["inbox_chars"] + r["ctolog_chars"]), -r["wakes"]))
    return out


def day_totals(rs: list[dict], days: list[str]) -> list[dict]:
    tot = []
    for d in days:
        sel = [r for r in rs if r["day"] == d]
        n_turns = sum(r["turns_with_usage"] for r in sel)

        def wavg(k):
            num = sum((r[k] or 0) * r["turns_with_usage"] for r in sel)
            return round(num / n_turns) if n_turns else None
        tot.append({
            "day": d, "sessions": len({r["session_id"] for r in sel}),
            "wakes": sum(r["wakes"] for r in sel),
            **{f"wakes_{k}": sum(r[f"wakes_{k}"] for r in sel) for k in WAKE_KINDS},
            "inbox_chars": sum(r["inbox_chars"] for r in sel),
            "letters": sum(r["letters"] for r in sel),
            "ctolog_chars": sum(r["ctolog_chars"] for r in sel),
            "ctolog_lines": sum(r["ctolog_lines"] for r in sel),
            "peer_msg_chars": sum(r["peer_msg_chars"] for r in sel),
            "cache_read_first_call_avg": wavg("cache_read_first_call_avg"),
            "cache_write_first_call_avg": wavg("cache_write_first_call_avg"),
            "cache_read_per_wake_avg": wavg("cache_read_per_wake_avg"),
        })
    return tot


def _fmt(v) -> str:
    return "-" if v is None else f"{v:,}" if isinstance(v, int) else str(v)


def render(data: dict, top: int, include_headless: bool = False) -> str:
    rs = rows(data, include_headless)
    tots = day_totals(rs, data["days"])
    cov = data["coverage"]
    L = [f"org mail baseline -- every number MEASURED from transcripts; Thai days {data['days'][0]} .. {data['days'][-1]}",
         "wakes = prompt submissions, split h/p/t/m/l/o: h=typed in the pane (the CEO, or a session typing",
         "  via tmux) p=peer message t=background-task notice m=mailbox wake marker l=worker kickoff o=other",
         "inbox / ctolog = characters hook-inbox.py / hook-log-prompt.py put into context; letters = mail drained,",
         "  lines = cto.log lines surfaced; peer = characters of peer messages that woke the session",
         "cr1 / cw1 = cache read / cache write tokens on a wake's first call (avg); crT = cache read summed over the turn (avg)",
         ""]
    cols = (f"{'wakes':>6} {'h/p/t/m/l/o':>16} {'inbox':>8} {'letters':>7} {'ctolog':>8} {'lines':>6} "
            f"{'peer':>8} {'cr1':>8} {'cw1':>8} {'crT':>11}")

    def nums(r: dict) -> str:
        hp = "/".join(str(r[f"wakes_{k}"]) for k in WAKE_KINDS)
        return (f"{r['wakes']:>6} {hp:>16} {_fmt(r['inbox_chars']):>8} {r['letters']:>7} "
                f"{_fmt(r['ctolog_chars']):>8} {r['ctolog_lines']:>6} {_fmt(r['peer_msg_chars']):>8} "
                f"{_fmt(r['cache_read_first_call_avg']):>8} {_fmt(r['cache_write_first_call_avg']):>8} "
                f"{_fmt(r['cache_read_per_wake_avg']):>11}")
    L += ["DAY TOTALS", f"{'day':10} {'sess':>4} {cols}"]
    for t in tots:
        L.append(f"{t['day']:10} {t['sessions']:>4} {nums(t)}")
    L += ["", f"PER SESSION (top {top} per day by inbox+ctolog chars, then wakes)",
          f"{'day':10} {'session':8} {'kind':8} {'role':8} {cols}  title"]
    for d in data["days"]:
        for r in [r for r in rs if r["day"] == d][:top]:
            L.append(f"{r['day']:10} {r['session']:8} {str(r['kind']):8} {str(r['role'])[:8]:8} {nums(r)}  "
                     f"{(r['title'] or '')[:60]}")
    L += ["", f"coverage: {cov['files_scanned']} transcript files under {', '.join(cov['roots'])}"]
    n_headless = len({s for s, m in data["meta"].items() if m.get("kind") == "headless"})
    if n_headless and not include_headless:
        L.append(f"left out: {n_headless} headless `claude -p` sessions (no org hook runs there; --include-headless shows them)")
    for k in ("missing_roots", "unreadable"):
        if cov[k]:
            L.append(f"NOT MEASURED ({k}): {', '.join(cov[k][:10])}")
    L.append("NOT MEASURED: sessions of other unix users (e.g. SomPong) and other machines,"
             " unless their projects dir is passed with --root and is readable")
    return "\n".join(L)

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=4, help="Thai calendar days ending today (default 4: today + 3 before)")
    ap.add_argument("--root", action="append", type=Path, help="a Claude projects dir (repeatable)")
    ap.add_argument("--today", help="YYYY-MM-DD, Thai date the window ends on (default: now)")
    ap.add_argument("--top", type=int, default=15, help="sessions shown per day in the text table")
    ap.add_argument("--json", action="store_true", help="print rows + day totals as JSON")
    ap.add_argument("--include-headless", action="store_true", help="also count `claude -p` sessions")
    a = ap.parse_args(argv)
    today = dt.date.fromisoformat(a.today) if a.today else None
    data = collect(a.root or default_roots(), max(1, a.days), today)
    if a.json:
        rs = rows(data, a.include_headless)
        print(json.dumps({"measured": True, "days": data["days"], "day_totals": day_totals(rs, data["days"]),
                          "sessions": rs, "coverage": data["coverage"]}, ensure_ascii=False, indent=1))
    else:
        print(render(data, a.top, a.include_headless))
    return 0


if __name__ == "__main__":
    sys.exit(main())
