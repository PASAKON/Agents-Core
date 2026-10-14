"""Rename this host's org sessions to the CEO's 14 Oct naming rule (M10b).

A session cannot rename itself under the auto-mode classifier ([Tmux Self Drive],
2 of 3 sessions on 2026-10-14), so a Run card runs this script, pinned by sha.
It is the tracked form of CTO Main's one-off card RUN-20261014-0440-c195.

For every local tmux session a launcher started ("<role>-<sid>" for a C-level or a
Project Head, "sompong" for the COO), it finds the Claude session in that tmux
(the session record's "tmux" field, its UUID ending in the sid), computes the rule
name (lib/session_names: host emoji from self_host(), the C-level's persona from
policies/agents.yaml, a PH's lane from its .spawned_by and project from its
.project), and when the current name is off the rule, types "/rename <name>" into
that pane. Only into a pane whose prompt line (❯) is empty: never onto a draft,
never C-u (that would erase the CEO's own text). Workers are never touched.

    python tools/rename_to_rule.py            # dry run: one line per session
    python tools/rename_to_rule.py --apply    # type /rename where it is safe
    python tools/rename_to_rule.py --apply --session cto-c34459eb

Exit 0 when every off-rule session was renamed or had nothing to do, 1 when one
was skipped (busy prompt, no record), 2 on bad usage.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import config, session_names  # noqa: E402
from tools import live_sessions as ls  # noqa: E402

LOCKS_DIR = ROOT / "state" / "locks"
_TMUX_RE = re.compile(r"^(c[a-z]o|project_head)-([0-9a-f]{8})$")
_FIXED = {"sompong": "coo"}
_PROMPT = "❯"          # ❯, Claude Code's input line
TOPIC_MAX = 40


def tmux(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=10)


def tmux_sessions() -> list[str]:
    r = tmux("list-sessions", "-F", "#{session_name}")
    return r.stdout.split() if r.returncode == 0 else []


def records(host: str) -> list[dict]:
    """Live session records on this host that sit in a tmux."""
    out = []
    for d in ls.session_dirs(host):
        try:
            files = sorted(p for p in Path(d).iterdir() if ls._SESSION_FILE_RE.match(p.name))
        except OSError:
            continue
        for p in files:
            raw = ls._read_session_file(p)
            if raw is None:
                continue
            try:
                data = json.loads(raw)
                pid = int(data["pid"])
            except (ValueError, KeyError, TypeError):
                continue
            if not isinstance(data, dict) or not isinstance(data.get("tmux"), str):
                continue
            if ls.is_alive(pid, ls._proc_start(data.get("procStart"))):
                out.append(data)
    return out


def _read(name: str) -> str:
    try:
        return (LOCKS_DIR / name).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""


def topic_of(name: str) -> str:
    """The human topic to keep: " — <topic>" in a new name, "(<topic>)" after the
    #id in an old one. A state glyph in front is dropped (the rename is a fresh name)."""
    if " — " in name:
        return name.split(" — ", 1)[1].strip()
    m = re.search(r"#[0-9a-f]{6,12}\s+\((.*)\)\s*$", name)
    return m.group(1).strip() if m else ""


def rule_name(role: str, sid: str, host: str, current: str) -> tuple[str | None, str]:
    """(the rule name, "") or (None, why not)."""
    topic = topic_of(current)
    if role == "project_head":
        project = _read(f"project_head-{sid}.project")
        spawned = _read(f"project_head-{sid}.spawned_by").split(":")   # cxo:<lane>:<sid>
        lane = spawned[1] if len(spawned) == 3 else ""
        if not project or not lane:
            return None, "no .project/.spawned_by record"
        base = config.ph_session_name(sid, lane, project, host)
        if topic == project:
            topic = ""
    else:
        persona = config.persona_for(role)
        base = session_names.with_host(host, f"{role.upper()} ({persona})" if persona else role.upper())
    if topic:
        if len(topic) > TOPIC_MAX:
            topic = topic[:TOPIC_MAX].rstrip() + "…"
        base = f"{base} — {topic}"
    if any(unicodedata.category(c) in ls._BAD_CHARS for c in base):
        return None, "name would carry a control character"
    return base, ""


def prompt_is_empty(target: str) -> bool:
    """True when the last ❯ line in the pane holds no text."""
    r = tmux("capture-pane", "-p", "-t", target)
    if r.returncode != 0:
        return False
    lines = [l for l in r.stdout.splitlines() if _PROMPT in l]
    if not lines:
        return False
    rest = lines[-1].split(_PROMPT, 1)[1].replace("\xa0", " ").strip()
    return rest == ""


def plan(host: str, only: str | None = None) -> list[dict]:
    recs = records(host)
    out = []
    for s in tmux_sessions():
        if only and s != only:
            continue
        m = _TMUX_RE.match(s)
        role = m.group(1) if m else _FIXED.get(s)
        if not role:
            continue
        mine = [d for d in recs if d["tmux"].split(":", 1)[0] == s]
        if m:
            mine = [d for d in mine if str(d.get("sessionId", "")).endswith(m.group(2))]
        row = {"tmux": s, "role": role}
        if len(mine) != 1:
            out.append({**row, "action": "skip", "why": f"{len(mine)} live session records in it"})
            continue
        data = mine[0]
        sid = m.group(2) if m else str(data.get("sessionId", ""))[-8:]
        if role == "coo" and not ls._launcher_uuid("coo", str(data.get("sessionId", ""))):
            out.append({**row, "action": "skip", "why": "not the launcher's COO session"})
            continue
        current = str(data.get("name") or "")
        persona = config.persona_for(role) if role != "project_head" else None
        problem = session_names.rule_problem(current, role, sid, host, persona=persona or None)
        row.update(sid=sid, current=current)
        if problem is None:
            out.append({**row, "action": "ok"})
            continue
        want, why = rule_name(role, sid, host, current)
        if want is None:
            out.append({**row, "action": "skip", "why": why})
            continue
        out.append({**row, "action": "rename", "why": problem, "name": want,
                    "target": data["tmux"].split(":", 1)[0]})
    return out


def apply(row: dict) -> dict:
    if not prompt_is_empty(row["target"]):
        return {**row, "action": "skip", "why": "prompt line not empty (draft or busy screen)"}
    a = tmux("send-keys", "-t", row["target"], "-l", f"/rename {row['name']}")
    b = tmux("send-keys", "-t", row["target"], "Enter") if a.returncode == 0 else a
    if a.returncode or b.returncode:
        return {**row, "action": "skip", "why": "tmux send-keys failed"}
    return {**row, "action": "renamed"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="type /rename (default: dry run)")
    ap.add_argument("--session", help="only this tmux session")
    a = ap.parse_args(argv)
    host = config.self_host()
    rows = plan(host, a.session)
    if a.apply:
        rows = [apply(r) if r["action"] == "rename" else r for r in rows]
    for r in rows:
        tail = (f' "{r["current"]}" -> "{r["name"]}" ({r["why"]})' if "name" in r
                else (f' "{r.get("current", "")}"' if r["action"] == "ok" else f' ({r["why"]})'))
        print(f'{r["action"]:<8} {r["tmux"]}{tail}')
    if not rows:
        print("no org tmux session on this host")
    return 1 if any(r["action"] == "skip" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
