"""Rename service (M10b, Agents-Core #272): applies the sessions' own rename requests.

CEO 2026-10-14 11:50 (via CMO): sessions rename themselves and never ask him. A
session may not type into its own pane: an allow rule for that would let it type
any slash command into its own prompt. So `scripts/session-rename.sh` only writes
a request, the topic and a state glyph, to state/rename-requests/<role>-<sid>.json.
This service (root on Contabo, systemd, installed by one Run card) reads them, builds
the name itself with lib/session_names, and types exactly one line, "/rename <name>",
then Enter, into THAT session's pane, and only when its prompt line (❯) is empty
and no choice prompt is up. Otherwise it leaves the request for the next pass. It
never types onto a draft, never sends C-u, and never starts or moves the tmux
server (client commands only: capture-pane, send-keys).

The request carries no name, so nothing a session writes can reach the pane except
a topic: clean_topic() keeps letters, marks, digits, spaces and a few punctuation
marks, drops every control and format character (newline, ESC), strips a leading
"/", and cuts it to 40 characters.

    python tools/rename_service.py once          # one pass (tests, a manual run)
    python tools/rename_service.py run           # the service: a pass every 15 s
    python tools/rename_service.py preview --role cto --sid c34459eb --topic "x"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import config, session_names  # noqa: E402
from tools import live_sessions as ls  # noqa: E402

LOCKS_DIR = ROOT / "state" / "locks"
REQUESTS_DIR = ROOT / "state" / "rename-requests"
TOPIC_MAX = 40
NAME_MAX = 120
PREFIXES = ("", "✅", "⏸", "⛔")        # ✅ close, ⏸ save, ⛔ merged
RETRY_S = 120                                      # a sent rename that did not land is sent again
MAX_SENDS = 3
INTERVAL_S = 15
_BOX_RE = re.compile(r"^(c[a-z]o|project_head)-([0-9a-f]{8})$")
_FIXED_TMUX = {"coo": "sompong"}
_TOPIC_PUNCT = set(" -_.,:;()+#&'!?%")
_PROMPT = "❯"


# --- the name ----------------------------------------------------------------------

def clean_topic(text) -> str:
    """The only session-written text that reaches a pane. One line, no control or
    format character, no leading "/", letters/marks/digits/spaces/_TOPIC_PUNCT only."""
    text = unicodedata.normalize("NFC", str(text or ""))
    kept = []
    for c in text:
        cat = unicodedata.category(c)
        if cat[0] in "LMN" or c in _TOPIC_PUNCT:
            kept.append(c)
        elif cat[0] in "CZ":
            kept.append(" ")          # a newline or tab becomes a space, never a key
    topic = re.sub(r" {2,}", " ", "".join(kept)).strip().lstrip("/ ").strip()
    if len(topic) > TOPIC_MAX:
        topic = topic[:TOPIC_MAX].rstrip() + "…"
    return topic


def _read(name: str) -> str:
    try:
        return (LOCKS_DIR / name).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""


def build_name(role: str, sid: str, topic, prefix, host: str) -> str | None:
    """The rule name for a C-level or PH plus the cleaned topic, or None (no rule
    for this role, a PH with no project record, a prefix not in PREFIXES)."""
    prefix = str(prefix or "")
    if prefix not in PREFIXES:
        return None
    topic = clean_topic(topic)
    if role == "project_head":
        project = _read(f"project_head-{sid}.project")
        spawned = _read(f"project_head-{sid}.spawned_by").split(":")   # cxo:<lane>:<sid>
        lane = spawned[1] if len(spawned) == 3 else ""
        if not re.fullmatch(r"[A-Za-z0-9_]{1,40}", project) or not re.fullmatch(r"c[a-z]o", lane):
            return None
        base = config.ph_session_name(sid, lane, project, host)
        if topic == project:
            topic = ""
    elif re.fullmatch(r"c[a-z]o", role) and role != "ceo":
        persona = config.persona_for(role)
        if persona and not re.fullmatch(r"[A-Za-z]{2,32}", persona):
            return None
        base = session_names.with_host(host, f"{role.upper()} ({persona})" if persona else role.upper())
    else:
        return None
    name = base + (f" — {topic}" if topic else "")
    name = f"{prefix} {name}" if prefix else name
    if (len(name) > NAME_MAX or name.startswith("/")
            or any(unicodedata.category(c)[0] == "C" or c in "\n\r" for c in name)):
        return None
    return name


# --- the panes ---------------------------------------------------------------------

def tmux(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=10)


# A numbered choice with the cursor on it (maybe inside a │ box), plus a choice footer:
# a permission prompt or an on-screen question, the app's ✋ "waiting for you".
_CHOICE_RE = re.compile(r"^[\s\u2502\u2503|]*\u276f\s*\d+\.\s")
_CHOICE_HINTS = ("Do you want", "Esc to cancel", "to navigate", "Enter to select", "Would you like")


def pane_waiting(text: str) -> bool:
    """True when a pane's screen holds a choice prompt waiting on a person."""
    tail = text.splitlines()[-30:]
    return any(_CHOICE_RE.match(l) for l in tail) and any(h in l for l in tail for h in _CHOICE_HINTS)


def prompt_ready(screen: str) -> bool:
    """The last ❯ line is empty and no choice prompt (permission / question) is up."""
    if pane_waiting(screen):
        return False
    lines = [l for l in screen.splitlines() if _PROMPT in l]
    return bool(lines) and lines[-1].split(_PROMPT, 1)[1].replace("\xa0", " ").strip() == ""


def session_of(box: str, host: str) -> dict | None:
    """The one live session record in this box's launcher tmux, or None."""
    m = _BOX_RE.match(box)
    if not m:
        return None
    role, sid = m.groups()
    tmux_name = _FIXED_TMUX.get(role, box)
    hits = []
    for d in ls.session_dirs(host):
        try:
            files = [p for p in Path(d).iterdir() if ls._SESSION_FILE_RE.match(p.name)]
        except OSError:
            continue
        for p in files:
            raw = ls._read_session_file(p)
            try:
                data = json.loads(raw) if raw else None
                pid = int(data["pid"])
            except (ValueError, KeyError, TypeError):
                continue
            if not isinstance(data, dict) or str(data.get("tmux") or "").split(":", 1)[0] != tmux_name:
                continue
            uuid = str(data.get("sessionId") or "")
            if not uuid.endswith(sid) or not ls.is_alive(pid, ls._proc_start(data.get("procStart"))):
                continue
            if role == "coo" and not ls._launcher_uuid("coo", uuid):
                continue
            hits.append({"name": str(data.get("name") or ""), "pane": str(data["tmux"]).split(":", 1)[0],
                         "uuid": uuid})
    return hits[0] if len(hits) == 1 else None


# --- one pass ----------------------------------------------------------------------

def _load(path: Path) -> dict | None:
    try:
        if path.is_symlink() or path.stat().st_size > 4096:
            return None
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return d if isinstance(d, dict) else None


def _save(path: Path, d: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def once(host: str, now: float | None = None) -> list[str]:
    now = time.time() if now is None else now
    out = []
    try:
        paths = sorted(p for p in REQUESTS_DIR.iterdir() if p.suffix == ".json")
    except OSError:
        return out
    for path in paths:
        box = path.stem
        req = _load(path)
        if req is None or not _BOX_RE.match(box):
            out.append(f"drop     {box}: unreadable or not an org session")
            path.unlink(missing_ok=True)
            continue
        role, sid = box.split("-", 1)
        name = build_name(role, sid, req.get("topic"), req.get("prefix"), host)
        if name is None:
            out.append(f"drop     {box}: no rule name for it")
            path.unlink(missing_ok=True)
            continue
        sess = session_of(box, host)
        if sess is None:
            out.append(f"wait     {box}: no single live session in its tmux")
            continue
        if sess["name"] == name:
            out.append(f"done     {box}: {name}")
            path.unlink(missing_ok=True)
            continue
        sends = int(req.get("sends") or 0)
        if sends and now - float(req.get("sent_at") or 0) < RETRY_S:
            out.append(f"sent     {box}: waiting for it to land")
            continue
        if sends >= MAX_SENDS:
            out.append(f"gave up  {box}: {MAX_SENDS} sends did not land")
            path.unlink(missing_ok=True)
            continue
        screen = tmux("capture-pane", "-p", "-t", sess["pane"])
        if screen.returncode != 0 or not prompt_ready(screen.stdout):
            out.append(f"wait     {box}: prompt not empty")
            continue
        a = tmux("send-keys", "-t", sess["pane"], "-l", f"/rename {name}")
        if a.returncode == 0:
            tmux("send-keys", "-t", sess["pane"], "Enter")
        _save(path, {**req, "sends": sends + 1, "sent_at": now})
        out.append(f"renamed  {box}: {name}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("once")
    sub.add_parser("run")
    pv = sub.add_parser("preview")
    pv.add_argument("--role", required=True)
    pv.add_argument("--sid", required=True)
    pv.add_argument("--topic", default="")
    pv.add_argument("--prefix", default="")
    pv.add_argument("--host")
    pv.add_argument("--locks-dir", help="the calling checkout's state/locks")
    a = ap.parse_args(argv)
    if a.cmd == "preview":
        if a.locks_dir:
            global LOCKS_DIR
            LOCKS_DIR = Path(a.locks_dir)
        try:
            host = a.host or config.self_host()
        except Exception:
            host = ""
        name = build_name(a.role, a.sid, a.topic, a.prefix, host)
        print(name or "")
        return 0 if name else 1
    host = config.self_host()
    while True:
        for line in once(host):
            print(line, flush=True)
        if a.cmd == "once":
            return 0
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    sys.exit(main())
