#!/usr/bin/env python3
"""tools/session_diagram.py — the session map behind /session-worktree.

What the CEO asked for (2026-09-09): a left→right picture of the session —
"ซ้ายคือเริ่มต้น session: CEO ต้องการอะไร → มี task อะไรบ้าง ในแต่ละ block มี task ย่อย
1 2 3 4 5 แต่ละอันเสร็จหรือยัง → block ต่อไปติด task ก่อนหน้า … goal อาจต่อกัน หรือ
แยกกันคนละเส้น … บอกได้ว่าตอนนี้อยู่จุดไหน ออกนอกเส้นทางไปทางไหน" — with time per
block, built to spend as few tokens as possible while staying complete.

    START ──▶ [G1 ☑☑☑ 22:39→23:04·25m] ──▶ [G2 ☑☐☐ ◀ HERE] ──▶ [G4 ☐☐]
      └─────▶ [G3 ☑☐ ⚠ blocked]                 (separate line = separate row)
                   ╎↩ interrupt that came back      ╎ parked → LungNote, dead end

Token economy — the design rule (CEO 2026-09-09):
  * one JSON file per session, created on the FIRST /session-worktree only
    (never at /session-open; never unless asked): state/session-diagrams/<session>.json
  * later runs send a small PATCH (what changed), not the whole tree; the script
    re-renders everything and the Artifact tool republishes the SAME URL
  * the script stamps started/finished times itself on status transitions —
    nobody types times; minutes per block are derived
  * output is a short status block, never the picture and never a full tree
    unless --tree is asked

Commands (stdin = JSON):
  map      full map JSON → create/replace the session file, render, print status
  patch    delta JSON → merge, stamp, render, print status
  show     print status (add --tree for the 🌳 text tree)
  render   re-render the files from the session file (e.g. after a manual edit)
  sample / sample-patch   print example JSON

Outputs (basename = the session id, stable):
  <session>.json            the map (source of truth between runs)
  <session>.html            self-contained wide page (for PNG / local viewing)
  <session>.artifact.html   page body for the Artifact tool: wide map + narrow map,
                            switched by a CSS media query (desktop / phone)
  <session>.png             opt-in --png via headless Chrome; --send = Telegram opt-in

Drawn in the visual system of the `diagram-design` skill (cathrynlavery
v2.6.17, vendored under ~/.claude/skills/diagram-design): default editorial skin,
Instrument Serif / Geist / Geist Mono (+ Noto Thai), 4px grid, orthogonal r=8
connectors drawn before boxes, legend strip, accessible-SVG contract, and its
own scripts/self_check.py run on every render.

References inside a patch: "G2" = goal, "G2.3" = task 3 of G2, "D1" = detour.
Exit codes: 0 ok · 1 bad input · 2 self_check failed · 3 --send failed.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = ROOT / "state" / "session-diagrams"
SKILL_DIR = Path.home() / ".claude" / "skills" / "diagram-design"

# ---- diagram-design default skin (references/style-guide.md) -----------------
PAPER = "#f5f5f5"
INK = "#2d3142"
MUTED = "#4f5d75"
SOFT = "#7a8399"
ACCENT = "#eb6c36"
ACCENT_TINT = "rgba(235,108,54,0.08)"
ACCENT_05 = "rgba(235,108,54,0.05)"
RULE = "rgba(45,49,66,0.12)"
INK_02 = "rgba(45,49,66,0.02)"
INK_05 = "rgba(45,49,66,0.05)"
INK_20 = "rgba(45,49,66,0.20)"
INK_40 = "rgba(45,49,66,0.40)"
FONT_SANS = "'Geist', 'Noto Sans Thai', system-ui, sans-serif"
FONT_SERIF = "'Instrument Serif', 'Noto Serif Thai', serif"
FONT_MONO = "'Geist Mono', 'Noto Sans Thai', ui-monospace, monospace"
FONT_LINK = (
    "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1"
    "&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500;600"
    "&family=Noto+Sans+Thai:wght@400;600&family=Noto+Serif+Thai:wght@400&display=swap"
)

STATUSES = ("done", "doing", "todo", "blocked")
STATUS_EMOJI = {"done": "✅", "doing": "🔄", "todo": "⬜", "blocked": "🔴"}
STATUS_WORD = {"done": "DONE", "doing": "DOING", "todo": "TODO", "blocked": "BLOCKED"}
DETOUR_KINDS = ("interrupt", "parked")
TYPE_GLYPH = {
    "READ": "🔍", "RECON": "🔍", "RESEARCH": "📚", "ANALYZE": "🧠", "DECIDE": "🧠",
    "BUILD": "🔨", "FIX": "🔧", "DESIGN": "🎨", "SETUP": "⚙️", "TEST": "🧪",
    "VERIFY": "🧪", "SHIP": "🚀", "DOC": "📝", "CLOSE": "🏁", "GOAL": "🎯",
}
# block treatment = SKILL.md §5 table + type-kanban.md card states
TREATMENT = {
    "done": dict(fill=INK_05, stroke=MUTED, dash=None),          # store
    "doing": dict(fill=ACCENT_TINT, stroke=ACCENT, dash=None),   # focal
    "todo": dict(fill=INK_02, stroke=INK_20, dash="4,3"),        # optional
    "blocked": dict(fill=ACCENT_05, stroke=ACCENT, dash="4,4"),  # blocked card
}
CHIP_COLOR = {"done": MUTED, "doing": ACCENT, "todo": SOFT, "blocked": ACCENT}

# ---- geometry (everything on the 4px grid) -----------------------------------
M = 40                  # wide page margin
START_W, START_H = 200, 64
GOAL_W = 320
TASK_TIME_MIN_W = 300   # blocks at least this wide show each task's own time span
GAP = 48                # horizontal gap between columns (edges live here)
ROW_GAP = 32
HEADER_H = 68           # chips · title · time line · rule
TASK_ROW = 20
FOOT = 12
MAX_TASK_ROWS = 8
DETOUR_H, DETOUR_GAP = 40, 24
STUB = 8                # dead-end stub under a parked detour
PORT_Y = 24             # edges attach at the header band, not the block centre
NARROW_W, NM = 400, 24  # phone layout: page width and margin
TELEGRAM_PHOTO_MAX_SUM = 10000   # sendPhoto: width + height ≤ 10000 px

SAMPLE = {
    "entry_problem": "ทำให้ /session-worktree ปิดท้ายด้วยแผนที่ session ที่ CEO เปิดดูได้จากลิงก์เดียว",
    "start": "CEO อยากเห็นภาพรวม session เป็น diagram — goal, task ย่อย, จุดที่อยู่, ทางที่ออกนอกเส้น",
    "goals": [
        {"id": "G1", "title": "รับ diagram-design เข้าเป็น skill ของ org", "type": "SETUP",
         "tasks": [
             {"title": "clone + pin v2.6.17", "status": "done", "evidence": "2724fd2",
              "started_at": "2026-09-08T22:30", "finished_at": "2026-09-08T22:39"},
             {"title": "symlink ~/.claude/skills", "status": "done", "started_at": "2026-09-08T22:39", "finished_at": "2026-09-08T22:41"},
             {"title": "skill-report มองเห็น", "status": "done", "started_at": "2026-09-08T22:41", "finished_at": "2026-09-08T22:42"},
         ]},
        {"id": "G2", "title": "renderer: JSON → HTML ในระบบ diagram-design", "type": "BUILD", "depends_on": ["G1"],
         "tasks": [
             {"title": "vertical tree v1", "status": "done", "evidence": "1ca64bd",
              "started_at": "2026-09-08T22:45", "finished_at": "2026-09-08T23:04"},
             {"title": "goal map v2 ซ้าย→ขวา", "status": "doing", "started_at": "00:10"},
             {"title": "tests เขียว + self_check", "status": "todo", "type": "TEST"},
         ],
         "detours": [
             {"title": "WIP หายเพราะ session อื่น merge — park/unpark", "kind": "interrupt", "status": "done"},
             {"title": "Contabo: clone + Chromium", "kind": "parked", "status": "todo", "note": "LungNote 0c2b506c"},
         ]},
        {"id": "G3", "title": "/session-worktree ส่งลิงก์ Artifact ท้ายสรุป", "type": "DOC", "depends_on": ["G2"],
         "tasks": [
             {"title": "SKILL.md view 3", "status": "done", "started_at": "2026-09-08T23:10", "finished_at": "2026-09-08T23:20"},
             {"title": "publish + link บรรทัดสุดท้าย", "status": "todo"},
         ]},
        {"id": "G4", "title": "แยกเส้น: ตอบคำถาม CEO เรื่องช่องทางส่ง", "type": "ANALYZE",
         "tasks": [{"title": "ทำไม SomPong / ทำไมรูป / เรื่อง token", "status": "blocked", "blocked_on": "CEO ตอบข้อ 3"}]},
    ],
    "here": "G2.2",
}

SAMPLE_PATCH = {
    "set": {"G2.2": "done", "G2.3": "doing", "G4.1": "done"},
    "evidence": {"G2.2": "c3d5d2b"},
    "here": "G2.3",
    "add": {"tasks": {"G3": [{"title": "แก้ SKILL.md เป็น map + patch"}]},
            "detours": {"G3": [{"title": "CEO ขอถามก่อนออกแบบ", "kind": "interrupt", "status": "done"}]}},
}


# ---- time -----------------------------------------------------------------------
def now_local() -> datetime:
    """`SESSION_DIAGRAM_NOW=YYYY-MM-DDTHH:MM` pins the clock (tests)."""
    v = os.environ.get("SESSION_DIAGRAM_NOW", "").strip()
    if v:
        return datetime.strptime(v, "%Y-%m-%dT%H:%M")
    return datetime.now().replace(second=0, microsecond=0)


def parse_ts(raw: object, day: str) -> str:
    """Accept 'HH:MM' (on `day`), 'YYYY-MM-DDTHH:MM', or '' → normalized ISO minute or ''."""
    s = str(raw or "").strip()
    if not s:
        return ""
    if len(s) == 5 and s[2] == ":":
        return f"{day}T{s}"
    try:
        return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").strftime("%Y-%m-%dT%H:%M")
    except ValueError as exc:
        raise ValueError(f"bad time {s!r} (use HH:MM or YYYY-MM-DDTHH:MM)") from exc


def ts_dt(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M")


def fmt_hm(ts: str) -> str:
    return ts[11:16] if ts else ""


def fmt_minutes(mins: int) -> str:
    if mins < 60:
        return f"{mins} min"
    h, m = divmod(mins, 60)
    return f"{h}h {m:02d}m"


def span_text(started: str, finished: str, now: datetime) -> str:
    """'22:39→23:04 · 25 min' / '00:10→now · 12 min' / ''."""
    if not started:
        return ""
    a = ts_dt(started)
    if finished:
        b = ts_dt(finished)
        return f"{fmt_hm(started)}→{fmt_hm(finished)} · {fmt_minutes(max(0, int((b - a).total_seconds() // 60)))}"
    return f"{fmt_hm(started)}→now · {fmt_minutes(max(0, int((now - a).total_seconds() // 60)))}"


# ---- text metrics ------------------------------------------------------------
def _char_w(ch: str, mono: bool) -> float:
    """Advance width in em. Per character, never per script (style-guide.md)."""
    if unicodedata.combining(ch):
        return 0.0
    o = ord(ch)
    if o == 0x0E31 or 0x0E34 <= o <= 0x0E3A or 0x0E47 <= o <= 0x0E4E:
        return 0.0
    if o == 0x200B or o == 0xFE0F:
        return 0.0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 1.0
    if o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF:
        return 1.25
    if 0x0E00 <= o <= 0x0E7F:
        return 0.62
    return 0.62 if mono else 0.60


def text_width(s: str, size: float, mono: bool = False) -> float:
    return sum(_char_w(c, mono) for c in s) * size


def fit(s: str, size: float, max_w: float, mono: bool = False) -> str:
    if text_width(s, size, mono) <= max_w:
        return s
    out = ""
    for c in s:
        if text_width(out + c + "…", size, mono) > max_w:
            break
        out += c
    return out.rstrip() + "…"


def wrap(s: str, size: float, max_w: float, max_lines: int, mono: bool = False) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in s.split(" "):
        cand = (cur + " " + word).strip()
        if text_width(cand, size, mono) <= max_w:
            cur = cand
            continue
        if cur:
            lines.append(cur)
            cur = ""
        while text_width(word, size, mono) > max_w:
            piece = ""
            for c in word:
                if text_width(piece + c, size, mono) > max_w:
                    break
                piece += c
            lines.append(piece)
            word = word[len(piece):]
        cur = word
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = fit(lines[-1] + "…", size, max_w, mono)
    return lines or [""]


def up4(v: float) -> int:
    return int(-(-v // 4) * 4)


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


# ---- model -------------------------------------------------------------------
def _status(raw: object, where: str) -> str:
    s = str(raw or "todo").lower().strip()
    if s not in STATUSES:
        raise ValueError(f"{where}: status must be one of {STATUSES}, got {s!r}")
    return s


class Item:
    """Shared by tasks, goals and detours: status + auto-stamped times."""
    status: str
    started_at: str
    finished_at: str

    def stamp(self, old: str | None, now: datetime, creation: bool = False) -> None:
        """Called after a status change: doing/blocked start the clock, done stops it.
        At map creation an item that is already done has no clock to start —
        it stays timeless rather than pretending it took 0 minutes."""
        if old == self.status:
            return
        if creation and self.status == "done":
            return
        ts = now.strftime("%Y-%m-%dT%H:%M")
        if self.status in ("doing", "blocked") and not self.started_at:
            self.started_at = ts
        if self.status == "done":
            if not self.started_at:
                self.started_at = ts
            if not self.finished_at:
                self.finished_at = ts


class Task(Item):
    def __init__(self, raw: dict, n: int, goal_id: str, day: str):
        self.n = int(raw.get("n") or n)
        self.title = str(raw.get("title", "")).strip()
        if not self.title:
            raise ValueError(f"{goal_id}.{n}: title is required")
        self.status = _status(raw.get("status"), f"{goal_id}.{n}")
        self.type = str(raw.get("type") or "BUILD").upper().strip()
        self.evidence = str(raw.get("evidence") or "").strip()
        self.blocked_on = str(raw.get("blocked_on") or "").strip()
        self.started_at = parse_ts(raw.get("started_at"), day)
        self.finished_at = parse_ts(raw.get("finished_at"), day)
        if self.status == "blocked" and not self.blocked_on:
            self.blocked_on = "?"

    def to_dict(self) -> dict:
        d = {"n": self.n, "title": self.title, "status": self.status, "type": self.type}
        for k in ("evidence", "blocked_on", "started_at", "finished_at"):
            if getattr(self, k):
                d[k] = getattr(self, k)
        return d


class Detour(Item):
    def __init__(self, raw: dict, did: str, day: str):
        self.id = did
        self.title = str(raw.get("title", "")).strip()
        if not self.title:
            raise ValueError(f"detour {did}: title is required")
        self.kind = str(raw.get("kind") or "interrupt").lower().strip()
        if self.kind not in DETOUR_KINDS:
            raise ValueError(f"detour {did}: kind must be one of {DETOUR_KINDS}, got {self.kind!r}")
        self.status = _status(raw.get("status"), f"detour {did}")
        self.note = str(raw.get("note") or "").strip()
        self.started_at = parse_ts(raw.get("started_at"), day)
        self.finished_at = parse_ts(raw.get("finished_at"), day)

    def to_dict(self) -> dict:
        d = {"id": self.id, "title": self.title, "kind": self.kind, "status": self.status}
        for k in ("note", "started_at", "finished_at"):
            if getattr(self, k):
                d[k] = getattr(self, k)
        return d


class Goal(Item):
    def __init__(self, raw: dict, index: int, day: str, detour_seq: list[int]):
        self.id = str(raw.get("id") or f"G{index + 1}").strip()
        self.title = str(raw.get("title", "")).strip()
        if not self.title:
            raise ValueError(f"goal {self.id}: title is required")
        self.type = str(raw.get("type") or "GOAL").upper().strip()
        self.depends_on = [str(d).strip() for d in (raw.get("depends_on") or []) if str(d).strip()]
        self.blocked_on = str(raw.get("blocked_on") or "").strip()
        self.evidence = str(raw.get("evidence") or "").strip()
        self.tasks = [Task(t, i + 1, self.id, day) for i, t in enumerate(raw.get("tasks") or [])]
        self.detours = []
        for d in raw.get("detours") or []:
            did = str(d.get("id") or "").strip()
            if not did:
                detour_seq[0] += 1
                did = f"D{detour_seq[0]}"
            self.detours.append(Detour(d, did, day))
        self.status_override = _status(raw["status"], f"goal {self.id}") if raw.get("status") and not self.tasks else ""
        if raw.get("status") and self.tasks:
            self.status_override = _status(raw["status"], f"goal {self.id}") if raw.get("status_override") else ""
        self.started_at = parse_ts(raw.get("started_at"), day)
        self.finished_at = parse_ts(raw.get("finished_at"), day)
        self.status = self.status_override or self.infer_status()
        self.col = self.row = self.x = self.y = self.h = 0

    def infer_status(self) -> str:
        if self.status_override:
            return self.status_override
        if not self.tasks:
            return "todo"
        st = {t.status for t in self.tasks}
        if "blocked" in st:
            return "blocked"
        if "doing" in st:
            return "doing"
        if st == {"done"}:
            return "done"
        if "done" in st:
            return "doing"
        return "todo"

    def blocked_reason(self) -> str:
        if self.blocked_on:
            return self.blocked_on
        t = next((t for t in self.tasks if t.status == "blocked"), None)
        return t.blocked_on if t else "?"

    def stamp(self, old: str | None, now: datetime, creation: bool = False) -> None:
        if self.tasks:
            return                    # a goal with tasks takes its clock from the tasks
        super().stamp(old, now, creation)

    def times(self) -> tuple[str, str]:
        """Derived from the tasks when there are any; else the goal's own stamps."""
        if self.tasks:
            started = min((t.started_at for t in self.tasks if t.started_at), default="")
            finished = ""
            if self.status == "done" and all(t.finished_at for t in self.tasks):
                finished = max(t.finished_at for t in self.tasks)
            return started, finished
        return self.started_at, self.finished_at

    def height(self) -> int:
        rows = min(len(self.tasks), MAX_TASK_ROWS)
        h = HEADER_H + rows * TASK_ROW + FOOT
        if self.status == "blocked":
            h += 16
        return up4(h)

    def footprint(self) -> int:
        f = self.height() + len(self.detours) * (DETOUR_GAP + DETOUR_H)
        if any(d.kind == "parked" for d in self.detours):
            f += STUB
        return f

    def to_dict(self) -> dict:
        d = {"id": self.id, "title": self.title, "type": self.type, "depends_on": self.depends_on,
             "status": self.status, "tasks": [t.to_dict() for t in self.tasks],
             "detours": [x.to_dict() for x in self.detours]}
        if self.status_override:
            d["status_override"] = True
        for k in ("blocked_on", "evidence", "started_at", "finished_at"):
            if getattr(self, k):
                d[k] = getattr(self, k)
        return d


class Session:
    def __init__(self, data: dict, session_id: str | None = None):
        if not isinstance(data, dict):
            raise ValueError("top level must be an object")
        self.entry_problem = str(data.get("entry_problem", "")).strip()
        if not self.entry_problem:
            raise ValueError("entry_problem is required")
        self.start = str(data.get("start") or self.entry_problem).strip()
        self.session = str(session_id or data.get("session") or _session_id_from_env() or "session")
        self.date = str(data.get("date") or now_local().strftime("%Y-%m-%d"))
        self.created_at = str(data.get("created_at") or now_local().strftime("%Y-%m-%dT%H:%M"))
        self.runs = int(data.get("runs") or 0)
        raw_goals = data.get("goals") or []
        if not isinstance(raw_goals, list) or not raw_goals:
            raise ValueError("goals must be a non-empty list")
        seq = [0]
        self.goals = [Goal(g, i, self.date, seq) for i, g in enumerate(raw_goals)]
        used = [int(d.id[1:]) for g in self.goals for d in g.detours if d.id[:1] == "D" and d.id[1:].isdigit()]
        self._detour_seq = max([seq[0]] + used)     # a loaded map must not re-issue D1
        self._validate()
        self.here_goal: str | None = None
        self.here_task: int | None = None
        self.set_here(data.get("here"))
        layout(self)

    # -- structure ---------------------------------------------------------------
    def _validate(self) -> None:
        ids = [g.id for g in self.goals]
        if len(set(ids)) != len(ids):
            raise ValueError(f"goal ids must be unique: {ids}")
        for g in self.goals:
            for d in g.depends_on:
                if d not in ids:
                    raise ValueError(f"goal {g.id} depends on unknown goal {d!r}")
        dids = [d.id for g in self.goals for d in g.detours]
        if len(set(dids)) != len(dids):
            raise ValueError(f"detour ids must be unique: {dids}")

    def goal(self, gid: str) -> Goal:
        for g in self.goals:
            if g.id == gid:
                return g
        raise ValueError(f"unknown goal {gid!r}")

    def ref(self, key: str):
        """'G2' → Goal, 'G2.3' → Task, 'D1' → Detour."""
        key = str(key).strip()
        if "." in key:
            gid, n = key.rsplit(".", 1)
            g = self.goal(gid)
            for t in g.tasks:
                if str(t.n) == n:
                    return t
            raise ValueError(f"unknown task {key!r}")
        for g in self.goals:
            for d in g.detours:
                if d.id == key:
                    return d
        return self.goal(key)

    def set_here(self, here: object) -> None:
        if isinstance(here, dict):
            gid = str(here.get("goal") or "").strip()
            task = here.get("task")
            here = f"{gid}.{task}" if gid and task not in (None, "") else gid
        here = str(here or "").strip()
        if here:
            obj = self.ref(here)
            if isinstance(obj, Task):
                self.here_goal, self.here_task = here.rsplit(".", 1)[0], obj.n
            elif isinstance(obj, Goal):
                self.here_goal, self.here_task = obj.id, None
            else:
                raise ValueError("here must point at a goal or a task, not a detour")
            return
        self.here_goal = self.here_task = None
        for g in self.goals:                      # infer: the first thing in progress
            t = next((t for t in g.tasks if t.status == "doing"), None)
            if t:
                self.here_goal, self.here_task = g.id, t.n
                return
            if g.status == "doing":
                self.here_goal = g.id
                return

    def refresh(self) -> None:
        for g in self.goals:
            g.status = g.infer_status()
        self._validate()
        layout(self)

    # -- patch -------------------------------------------------------------------
    def apply_patch(self, delta: dict, now: datetime) -> list[str]:
        """Merge a delta; returns human-readable change lines. Auto-stamps times."""
        if not isinstance(delta, dict):
            raise ValueError("patch must be an object")
        changes: list[str] = []
        for k in ("entry_problem", "start"):
            if delta.get(k):
                setattr(self, k, str(delta[k]).strip())
                changes.append(f"{k} updated")
        add = delta.get("add") or {}
        for raw in add.get("goals") or []:
            seq = [self._detour_seq]
            g = Goal(raw, len(self.goals), self.date, seq)
            self._detour_seq = seq[0]
            self.goals.append(g)
            for t in g.tasks:
                t.stamp(None, now)
            g.stamp(None, now)
            changes.append(f"+ goal {g.id}")
        for gid, raws in (add.get("tasks") or {}).items():
            g = self.goal(gid)
            for raw in raws:
                t = Task(raw, len(g.tasks) + 1, g.id, self.date)
                t.n = len(g.tasks) + 1
                g.tasks.append(t)
                t.stamp(None, now)
                changes.append(f"+ task {g.id}.{t.n} {t.title}")
        for gid, raws in (add.get("detours") or {}).items():
            g = self.goal(gid)
            for raw in raws:
                did = str(raw.get("id") or "").strip()
                if not did:
                    self._detour_seq += 1
                    did = f"D{self._detour_seq}"
                d = Detour(raw, did, self.date)
                g.detours.append(d)
                d.stamp(None, now)
                changes.append(f"+ detour {d.id} ({d.kind}) {d.title}")
        for key, val in (delta.get("title") or {}).items():
            self.ref(key).title = str(val).strip()
            changes.append(f"{key} title → {val}")
        for key, val in (delta.get("evidence") or {}).items():
            obj = self.ref(key)
            if isinstance(obj, Detour):
                obj.note = str(val).strip()
            else:
                obj.evidence = str(val).strip()
            changes.append(f"{key} evidence → {val}")
        for key, val in (delta.get("blocked") or {}).items():
            obj = self.ref(key)
            obj.blocked_on = str(val).strip()
            old = obj.status
            obj.status = "blocked"
            if isinstance(obj, Goal):
                obj.status_override = "blocked" if not obj.tasks else ""
            obj.stamp(old, now)
            changes.append(f"{key} blocked · รอ {val}")
        for key, val in (delta.get("set") or {}).items():
            obj = self.ref(key)
            new = _status(val, key)
            old = obj.status
            obj.status = new
            if isinstance(obj, Goal):
                obj.status_override = new if (not obj.tasks or new != obj.infer_status()) else ""
                if new != "blocked":
                    obj.blocked_on = ""
            elif new != "blocked":
                obj.blocked_on = ""
            obj.stamp(old, now)
            if old != new:
                changes.append(f"{key} {old} → {new}")
        for key, val in (delta.get("time") or {}).items():          # manual override, rare
            obj = self.ref(key)
            if isinstance(val, dict):
                if val.get("started_at"):
                    obj.started_at = parse_ts(val["started_at"], self.date)
                if val.get("finished_at"):
                    obj.finished_at = parse_ts(val["finished_at"], self.date)
                changes.append(f"{key} time set")
        for g in self.goals:
            old = g.status
            g.status = g.infer_status()
            g.stamp(old, now)
        if "here" in delta:
            self.set_here(delta.get("here"))
        else:
            cur = self.ref(f"{self.here_goal}.{self.here_task}" if self.here_task else self.here_goal) if self.here_goal else None
            if cur is None or cur.status in ("done",):
                self.set_here(None)
        self.refresh()
        return changes

    # -- numbers -----------------------------------------------------------------
    def counts(self) -> dict:
        tasks = [t for g in self.goals for t in g.tasks]
        blocked = [f"{g.id}.{t.n}" for g in self.goals for t in g.tasks if t.status == "blocked"]
        blocked += [g.id for g in self.goals if g.status == "blocked" and not any(t.status == "blocked" for t in g.tasks)]
        return {
            "goals_done": sum(1 for g in self.goals if g.status == "done"), "goals": len(self.goals),
            "tasks_done": sum(1 for t in tasks if t.status == "done"), "tasks": len(tasks),
            "blocked": len(blocked), "blocked_keys": blocked,
            "detours": sum(len(g.detours) for g in self.goals),
            "parked": sum(1 for g in self.goals for d in g.detours if d.kind == "parked"),
        }

    def elapsed(self, now: datetime) -> str:
        starts = [ts for g in self.goals for ts in [g.times()[0]] if ts]
        starts += [d.started_at for g in self.goals for d in g.detours if d.started_at]
        if not starts:
            return ""
        first = ts_dt(min(starts))
        all_done = all(g.status == "done" for g in self.goals)
        ends = [ts for g in self.goals for ts in [g.times()[1]] if ts]
        last = ts_dt(max(ends)) if (all_done and ends) else now
        return fmt_minutes(max(0, int((last - first).total_seconds() // 60)))

    def type_tally(self) -> list[tuple[str, int]]:
        tally: dict[str, int] = {}
        for g in self.goals:
            for t in g.tasks:
                tally[t.type] = tally.get(t.type, 0) + 1
        return sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))

    def here_text(self) -> str:
        if not self.here_goal:
            return "—"
        g = self.goal(self.here_goal)
        if self.here_task:
            t = next(t for t in g.tasks if t.n == self.here_task)
            return f"{g.id}.{t.n} — {t.title}"
        return f"{g.id} — {g.title}"

    # -- persistence -------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "session": self.session, "date": self.date, "created_at": self.created_at, "runs": self.runs,
            "entry_problem": self.entry_problem, "start": self.start,
            "goals": [g.to_dict() for g in self.goals],
            "here": (f"{self.here_goal}.{self.here_task}" if self.here_task else self.here_goal) or "",
        }

    @classmethod
    def load(cls, path: Path) -> "Session":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")


def _session_id_from_env() -> str | None:
    """`<role>-<id>` from the launcher env, e.g. cto-576f0aff. CXO_SESSION is a
    0/1 flag, not an id — the id lives in <ROLE>_SESSION_ID."""
    role = os.environ.get("CXO_ROLE", "").strip().lower()
    candidates = [f"{role.upper()}_SESSION_ID"] if role else []
    candidates += ["CXO_SESSION_ID", "CTO_SESSION_ID"]
    for var in candidates:
        v = os.environ.get(var, "").strip()
        if len(v) >= 4:
            return f"{role}-{v}" if role else v
    return None


# ---- layout: columns by dependency depth, rows = separate lines --------------
def layout(s: Session) -> None:
    by_id = {g.id: g for g in s.goals}
    depth: dict[str, int] = {}

    def d(gid: str, seen: tuple = ()) -> int:
        if gid in depth:
            return depth[gid]
        if gid in seen:
            raise ValueError(f"dependency cycle through goal {gid}")
        g = by_id[gid]
        depth[gid] = 0 if not g.depends_on else 1 + max(d(x, seen + (gid,)) for x in g.depends_on)
        return depth[gid]

    for g in s.goals:
        g.col = d(g.id)
    taken: set[tuple[int, int]] = set()
    for g in s.goals:
        row = by_id[g.depends_on[0]].row if g.depends_on else 0
        while (g.col, row) in taken:
            row += 1
        g.row = row
        taken.add((g.col, row))
    s.ncols = max(g.col for g in s.goals) + 1
    s.nrows = max(g.row for g in s.goals) + 1
    s.row_h = [max([g.footprint() for g in s.goals if g.row == r] or [START_H]) for r in range(s.nrows)]


def col_x(c: int) -> int:
    return M + START_W + GAP + c * (GOAL_W + GAP)


def ordered(s: Session) -> list[Goal]:
    """Reading order for the narrow layout and the text tree: by row, then column."""
    return sorted(s.goals, key=lambda g: (g.row, g.col, s.goals.index(g)))


# ---- text outputs ------------------------------------------------------------
def status_text(s: Session, now: datetime, artifact: Path | None = None) -> str:
    c = s.counts()
    parts = [f"goals {c['goals_done']}/{c['goals']}", f"tasks {c['tasks_done']}/{c['tasks']}", f"🔴 {c['blocked']}"]
    if c["detours"]:
        parts.append(f"↪ {c['detours']} detour" + ("s" if c["detours"] > 1 else "") + (f" ({c['parked']} parked)" if c["parked"] else ""))
    el = s.elapsed(now)
    if el:
        parts.append(f"⏱ {el}")
    lines = ["📊 " + " · ".join(parts), f"📍 {s.here_text()}"]
    for key in c["blocked_keys"]:
        obj = s.ref(key)
        why = obj.blocked_on if isinstance(obj, Task) else obj.blocked_reason()
        lines.append(f"🔴 {key} — รอ {why}")
    return "\n".join(lines)


def tree_text(s: Session, now: datetime) -> str:
    lines = [f"🌳 SESSION MAP — {s.date} · {s.session} · run #{s.runs}", f"🎯 main: {s.entry_problem}",
             f"▶ start: {s.start}", "│"]
    for g in ordered(s):
        dep = f" (after {', '.join(g.depends_on)})" if g.depends_on else ""
        st, fi = g.times()
        span = span_text(st, fi, now)
        here = "  ⬅️ อยู่ตรงนี้" if (s.here_goal == g.id and s.here_task is None) else ""
        lines.append(f"├─ {STATUS_EMOJI[g.status]} {g.id}  {TYPE_GLYPH.get(g.type, '🎯')} {g.title}{dep}"
                     + (f"  ⏱ {span}" if span else "") + here
                     + (f" · BLOCKED: รอ {g.blocked_reason()}" if g.status == "blocked" else ""))
        kids = len(g.tasks) + len(g.detours)
        k = 0
        for t in g.tasks:
            k += 1
            pre = "│  " + ("└─ " if k == kids else "├─ ")
            here = "  ⬅️ อยู่ตรงนี้" if (s.here_goal == g.id and s.here_task == t.n) else ""
            span = span_text(t.started_at, t.finished_at, now)
            lines.append(f"{pre}{STATUS_EMOJI[t.status]} {g.id}.{t.n}  {TYPE_GLYPH.get(t.type, '🔨')} {t.type:<6} — {t.title}"
                         + (f" ............. {t.evidence}" if t.evidence else "")
                         + (f"  ⏱ {span}" if span else "") + here
                         + (f" · BLOCKED: รอ {t.blocked_on}" if t.status == "blocked" else ""))
        for d in g.detours:
            k += 1
            pre = "│  " + ("└─ " if k == kids else "├─ ")
            tail = " ↩ กลับเข้าเส้น" if d.kind == "interrupt" else f" ⊥ PARKED{(' · ' + d.note) if d.note else ''}"
            lines.append(f"{pre}{STATUS_EMOJI[d.status]} {d.id} ↪ {d.kind.upper()} — {d.title}{tail}")
    lines.append(f"└─ {'✅' if all(g.status == 'done' for g in s.goals) else '⬜'} 🏁 CLOSE — Done · Close Session")
    lines.append("")
    lines.append(status_text(s, now))
    return "\n".join(lines)


# ---- SVG primitives ----------------------------------------------------------
def _text(x: float, y: float, s: str, size: float, fill: str, family: str, *,
          weight: str | None = None, anchor: str | None = None, ls: str | None = None) -> str:
    attrs = [f'x="{x:g}"', f'y="{y:g}"', f'fill="{fill}"', f'font-size="{size:g}"',
             f'font-family="{esc(family)}"']
    if weight:
        attrs.append(f'font-weight="{weight}"')
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    if ls:
        attrs.append(f'letter-spacing="{ls}"')
    return f"<text {' '.join(attrs)}>{esc(s)}</text>"


def _chip(x: int, y: int, label: str, color: str) -> tuple[str, int]:
    """Rectangular type tag (rx=2, never a pill). Returns (svg, width)."""
    w = max(28, up4(text_width(label, 8, mono=True) * 1.08 + 12))
    svg = (f'<rect x="{x}" y="{y}" width="{w}" height="12" rx="2" fill="transparent" '
           f'stroke="{color}" stroke-width="0.8"/>'
           + _text(x + w / 2, y + 9, label, 8, color, FONT_MONO, anchor="middle", ls="0.08em"))
    return svg, w


def _elbow(x1: int, y1: int, x2: int, y2: int, mid: int) -> str:
    """Orthogonal connector with r=8 elbows (type-architecture.md); a plain
    line when the endpoints share a y."""
    if y1 == y2:
        return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTED}" '
                f'stroke-width="1.2" marker-end="url(#arrow)"/>')
    sgn = 1 if y2 > y1 else -1
    d = (f"M {x1},{y1} H {mid - 8} Q {mid},{y1} {mid},{y1 + 8 * sgn} V {y2 - 8 * sgn} "
         f"Q {mid},{y2} {mid + 8},{y2} H {x2}")
    return f'<path d="{d}" fill="none" stroke="{MUTED}" stroke-width="1.2" marker-end="url(#arrow)"/>'


def _vline(x: int, y1: int, y2: int, dashed: bool = True, arrow: bool = True) -> str:
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    mk = ' marker-end="url(#arrow)"' if arrow else ""
    return f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{MUTED}" stroke-width="1"{dash}{mk}/>'


def draw_goal(parts: list[str], g: Goal, x: int, y: int, w: int, s: Session, now: datetime,
              extra_chips: list[str] | None = None) -> int:
    """Draw one goal block (+ its detours below). Returns the footprint height."""
    h = g.height()
    is_here = s.here_goal == g.id
    status = g.status
    t = TREATMENT["doing" if (is_here and status in ("todo", "doing")) else status]
    dash = f' stroke-dasharray="{t["dash"]}"' if t["dash"] else ""
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PAPER}"/>')
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{t["fill"]}" '
                 f'stroke="{t["stroke"]}" stroke-width="{1.2 if is_here else 1}"{dash}/>')
    cx = x + 12
    if status == "blocked":
        parts.append(f'<rect x="{x + 4}" y="{y + 8}" width="4" height="32" rx="1" fill="{ACCENT}"/>')
        cx = x + 16
    for label, color in [(g.id, CHIP_COLOR[status]), (STATUS_WORD[status], CHIP_COLOR[status])] \
            + ([(g.type, INK_40)] if g.type != "GOAL" else []) + [(c, SOFT) for c in (extra_chips or [])]:
        chip, cw = _chip(cx, y + 12, label, color)
        parts.append(chip)
        cx += cw + 4
    if is_here and s.here_task is None:
        parts.append(_text(x + w - 12, y + 21, "◀ HERE", 8, ACCENT, FONT_MONO, anchor="end", ls="0.12em"))
    parts.append(_text(x + 12, y + 40, fit(g.title, 12, w - 24), 12, INK, FONT_SANS, weight="600"))
    st, fi = g.times()
    span = span_text(st, fi, now)
    parts.append(_text(x + 12, y + 53, span or "—", 8, MUTED if span else SOFT, FONT_MONO, ls="0.04em"))
    parts.append(f'<line x1="{x + 12}" y1="{y + 60}" x2="{x + w - 12}" y2="{y + 60}" stroke="{RULE}" stroke-width="0.8"/>')
    rows = g.tasks if len(g.tasks) <= MAX_TASK_ROWS else g.tasks[:MAX_TASK_ROWS - 1]
    for i, tk in enumerate(rows):
        ry = y + HEADER_H + i * TASK_ROW
        here_task = is_here and s.here_task == tk.n
        if tk.status == "done":
            sq = f'fill="{MUTED}" stroke="{MUTED}"'
        elif tk.status == "blocked":
            sq = f'fill="{ACCENT}" stroke="{ACCENT}"'
        elif tk.status == "doing" or here_task:
            sq = f'fill="transparent" stroke="{ACCENT}"'
        else:
            sq = f'fill="transparent" stroke="{INK_40}"'
        parts.append(f'<rect x="{x + 12}" y="{ry + 4}" width="8" height="8" rx="1" {sq} stroke-width="1"/>')
        parts.append(_text(x + 26, ry + 11, str(tk.n), 8, SOFT, FONT_MONO))
        label, color = tk.title, INK
        if tk.status == "blocked":
            label, color = f"{tk.title} · รอ {tk.blocked_on}", ACCENT
        elif tk.status == "done":
            color = MUTED
        elif tk.status == "doing" or here_task:
            color = ACCENT
        right = 12
        tspan = span_text(tk.started_at, tk.finished_at, now)
        if here_task:
            right += up4(text_width("◀ HERE", 8, mono=True) * 1.1 + 12)
            parts.append(_text(x + w - 12, ry + 11, "◀ HERE", 8, ACCENT, FONT_MONO, anchor="end", ls="0.12em"))
        elif tspan and w >= TASK_TIME_MIN_W:
            right += up4(text_width(tspan, 8, mono=True) + 12)
            parts.append(_text(x + w - 12, ry + 11, tspan, 8, SOFT, FONT_MONO, anchor="end"))
        parts.append(_text(x + 40, ry + 11, fit(label, 10, w - 40 - right), 10, color, FONT_SANS,
                           weight="600" if here_task else None))
    if len(g.tasks) > MAX_TASK_ROWS:
        ry = y + HEADER_H + (MAX_TASK_ROWS - 1) * TASK_ROW
        parts.append(_text(x + 40, ry + 11, f"+{len(g.tasks) - MAX_TASK_ROWS + 1} more", 9, SOFT, FONT_MONO))
    if status == "blocked":
        parts.append(_text(x + 12, y + h - 8, fit(f"BLOCKED · รอ {g.blocked_reason()}", 9, w - 24, mono=True),
                           9, ACCENT, FONT_MONO))
    # detours hang below the block: interrupt = down and back up; parked = down to a dead end
    dy = y + h
    for d in g.detours:
        top = dy + DETOUR_GAP
        parts.append(_vline(x + 24, dy, top))
        if d.kind == "interrupt":
            parts.append(_vline(x + w - 24, top, dy))
        parts.append(f'<rect x="{x}" y="{top}" width="{w}" height="{DETOUR_H}" rx="6" fill="{PAPER}"/>')
        dt = TREATMENT["done" if d.status == "done" else "todo"]
        ddash = f' stroke-dasharray="{dt["dash"]}"' if dt["dash"] else ""
        parts.append(f'<rect x="{x}" y="{top}" width="{w}" height="{DETOUR_H}" rx="6" fill="{dt["fill"]}" '
                     f'stroke="{dt["stroke"]}" stroke-width="1"{ddash}/>')
        chip, cw = _chip(x + 12, top + 8, "PARKED" if d.kind == "parked" else "DETOUR", SOFT if d.kind == "parked" else MUTED)
        parts.append(chip)
        tail = ("↩ back on the line" if d.status == "done" else "↩ returns when done") if d.kind == "interrupt" \
            else ("⊥ " + (d.note or "parked"))
        parts.append(_text(x + w - 12, top + 17, fit(tail, 8, w - 24 - cw - 20, mono=True), 8,
                           SOFT, FONT_MONO, anchor="end"))
        parts.append(_text(x + 12, top + 32, fit(d.title, 10, w - 24), 10, MUTED, FONT_SANS))
        dy = top + DETOUR_H
        if d.kind == "parked":
            parts.append(_vline(x + 24, dy, dy + STUB, arrow=False))
            parts.append(f'<line x1="{x + 12}" y1="{dy + STUB}" x2="{x + 36}" y2="{dy + STUB}" stroke="{MUTED}" stroke-width="1.2"/>')
            dy += STUB
    return dy - y


def draw_legend(parts: list[str], y: int, x0: int, x1: int, s: Session, now: datetime, compact: bool) -> int:
    """Legend strip + counts. Returns the y after it."""
    parts.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{RULE}" stroke-width="0.8"/>')
    parts.append(_text(x0, y + 16, "LEGEND", 8, MUTED, FONT_MONO, ls="0.18em"))
    c = s.counts()
    el = s.elapsed(now)
    counts = (f"GOALS {c['goals_done']}/{c['goals']} · TASKS {c['tasks_done']}/{c['tasks']} · "
              f"BLOCKED {c['blocked']}" + (f" · {el.upper()}" if el else ""))
    parts.append(_text(x1, y + 16, counts, 8, MUTED, FONT_MONO, anchor="end", ls="0.08em"))
    items = [("done", "Done"), ("doing", "Doing · here"), ("todo", "Not started"), ("blocked", "Blocked")]
    sw_y = y + 32
    lx = x0
    for key, label in items:
        t = TREATMENT[key]
        dash = f' stroke-dasharray="{t["dash"]}"' if t["dash"] else ""
        parts.append(f'<rect x="{lx}" y="{sw_y}" width="16" height="12" rx="2" fill="{t["fill"]}" '
                     f'stroke="{t["stroke"]}" stroke-width="1"{dash}/>')
        parts.append(_text(lx + 24, sw_y + 9, label, 9, MUTED, FONT_SANS))
        lx += 24 + up4(text_width(label, 9) + 32)
    if compact:
        sw_y += 20
        lx = x0
    parts.append(f'<line x1="{lx}" y1="{sw_y + 6}" x2="{lx + 28}" y2="{sw_y + 6}" stroke="{MUTED}" stroke-width="1.2" marker-end="url(#arrow)"/>')
    parts.append(_text(lx + 36, sw_y + 9, "Needs the previous goal", 9, MUTED, FONT_SANS))
    lx += 36 + up4(text_width("Needs the previous goal", 9) + 32)
    parts.append(f'<line x1="{lx}" y1="{sw_y + 6}" x2="{lx + 28}" y2="{sw_y + 6}" stroke="{MUTED}" stroke-width="1" stroke-dasharray="4,3" marker-end="url(#arrow)"/>')
    parts.append(_text(lx + 36, sw_y + 9, "Detour · ⊥ parked (dead end)", 9, MUTED, FONT_SANS))
    return sw_y + 12 + 20


def _defs() -> str:
    return (f'<defs><marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
            f'<polygon points="0 0, 8 3, 0 6" fill="{MUTED}"/></marker></defs>')


def _svg_open(slug: str, w: int, h: int, s: Session) -> str:
    c = s.counts()
    desc = (f"Session map: {c['goals_done']} of {c['goals']} goals done, {c['tasks_done']} of {c['tasks']} tasks done, "
            f"{c['blocked']} blocked, {c['detours']} detours, for the entry problem: {s.entry_problem}")
    return (f'<svg class="{slug}" viewBox="0 0 {w} {h}" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-labelledby="{slug}-title {slug}-desc">\n'
            f'<title id="{slug}-title">{esc(fit(s.entry_problem, 12, 700))}</title>\n'
            f'<desc id="{slug}-desc">{esc(desc)}</desc>\n{_defs()}\n'
            f'<rect width="100%" height="100%" fill="{PAPER}"/>\n')


# ---- wide layout (desktop): left → right --------------------------------------
def render_wide(s: Session, now: datetime) -> tuple[str, int, int]:
    W = col_x(s.ncols - 1) + GOAL_W + M
    parts: list[str] = []
    y = M
    el = s.elapsed(now)
    parts.append(_text(M, y + 8, f"SESSION MAP · {s.date} · {s.session} · RUN #{s.runs}" + (f" · {el.upper()}" if el else ""),
                       8, MUTED, FONT_MONO, ls="0.18em"))
    y += 40
    head = wrap(s.entry_problem, 24, W - 2 * M, 2)
    for i, ln in enumerate(head):
        parts.append(_text(M, y + i * 28, ln, 24, INK, FONT_SERIF))
    y_top = up4(y + (len(head) - 1) * 28 + 32)

    row_y: list[int] = []
    yy = y_top
    for r in range(s.nrows):
        row_y.append(yy)
        yy += s.row_h[r] + ROW_GAP
    for g in s.goals:
        g.x, g.y, g.h = col_x(g.col), row_y[g.row], g.height()

    roots = [g for g in s.goals if not g.depends_on]
    sx = M
    sy = roots[0].y + PORT_Y - START_H // 2 if len(roots) == 1 else up4(sum(g.y + PORT_Y for g in roots) / len(roots) - START_H // 2)

    # edges first (behind boxes): START → roots, dep → goal; fanned on shared edges (§6 rule 4)
    edges = [("START", g) for g in s.goals if not g.depends_on] + [(d, g) for g in s.goals for d in g.depends_on]
    out_n: dict[str, int] = {}
    in_n: dict[str, int] = {}
    for src, g in edges:
        out_n[src] = out_n.get(src, 0) + 1
        in_n[g.id] = in_n.get(g.id, 0) + 1
    out_k: dict[str, int] = {}
    in_k: dict[str, int] = {}
    gap_k: dict[int, int] = {}

    def port(y0: int, band: int, k: int, n: int) -> int:
        return y0 + PORT_Y if n == 1 else up4(y0 + band * (k + 1) / (n + 1))

    for src, g in edges:
        ko, out_k[src] = out_k.get(src, 0), out_k.get(src, 0) + 1
        ki, in_k[g.id] = in_k.get(g.id, 0), in_k.get(g.id, 0) + 1
        if src == "START":
            x1 = sx + START_W
            y1 = sy + START_H // 2 if out_n[src] == 1 else port(sy, START_H, ko, out_n[src])
        else:
            sg = s.goal(src)
            x1, y1 = sg.x + GOAL_W, port(sg.y, 48, ko, out_n[src])
        x2, y2 = g.x, port(g.y, 48, ki, in_n[g.id])
        kg, gap_k[g.col] = gap_k.get(g.col, 0), gap_k.get(g.col, 0) + 1
        parts.append(_elbow(x1, y1, x2, y2, x2 - GAP // 2 + (12 * (kg % 3) - 12)))

    parts.append(f'<rect x="{sx}" y="{sy}" width="{START_W}" height="{START_H}" rx="6" fill="{PAPER}"/>')
    parts.append(f'<rect x="{sx}" y="{sy}" width="{START_W}" height="{START_H}" rx="6" fill="#ffffff" stroke="{INK}" stroke-width="1"/>')
    chip, _w = _chip(sx + 12, sy + 8, "START", INK)
    parts.append(chip)
    for i, ln in enumerate(wrap(s.start, 10, START_W - 24, 2)):
        parts.append(_text(sx + 12, sy + 36 + i * 14, ln, 10, INK, FONT_SANS, weight="500"))
    for g in s.goals:
        draw_goal(parts, g, g.x, g.y, GOAL_W, s, now)
    y_leg = row_y[-1] + s.row_h[-1] + 28
    H = up4(draw_legend(parts, y_leg, M, W - M, s, now, compact=False))
    return _svg_open("session-map-wide", W, H, s) + "\n".join(parts) + "\n</svg>", W, H


# ---- narrow layout (phone): one block per row, top → bottom ---------------------
def render_narrow(s: Session, now: datetime) -> tuple[str, int, int]:
    W = NARROW_W
    bw = W - 2 * NM
    parts: list[str] = []
    y = NM
    el = s.elapsed(now)
    parts.append(_text(NM, y + 8, f"SESSION MAP · {s.date} · RUN #{s.runs}" + (f" · {el.upper()}" if el else ""),
                       8, MUTED, FONT_MONO, ls="0.14em"))
    y += 36
    head = wrap(s.entry_problem, 20, bw, 3)
    for i, ln in enumerate(head):
        parts.append(_text(NM, y + i * 24, ln, 20, INK, FONT_SERIF))
    y = up4(y + (len(head) - 1) * 24 + 28)
    # START
    parts.append(f'<rect x="{NM}" y="{y}" width="{bw}" height="{START_H}" rx="6" fill="#ffffff" stroke="{INK}" stroke-width="1"/>')
    chip, _w = _chip(NM + 12, y + 8, "START", INK)
    parts.append(chip)
    for i, ln in enumerate(wrap(s.start, 10, bw - 24, 2)):
        parts.append(_text(NM + 12, y + 36 + i * 14, ln, 10, INK, FONT_SANS, weight="500"))
    prev_bottom = y + START_H
    prev: Goal | None = None
    for g in ordered(s):
        gy = prev_bottom + 24
        links_prev = (prev is None and not g.depends_on) or (prev is not None and prev.id in g.depends_on)
        if links_prev:
            parts.append(f'<line x1="{NM + 40}" y1="{prev_bottom}" x2="{NM + 40}" y2="{gy}" stroke="{MUTED}" '
                         f'stroke-width="1.2" marker-end="url(#arrow)"/>')
        chips = [] if links_prev else ([f"AFTER {', '.join(g.depends_on)}"] if g.depends_on else [f"LINE {g.row + 1}"])
        fp = draw_goal(parts, g, NM, gy, bw, s, now, extra_chips=chips)
        prev_bottom = gy + fp
        prev = g
    H = up4(draw_legend(parts, prev_bottom + 28, NM, W - NM, s, now, compact=True))
    return _svg_open("session-map-narrow", W, H, s) + "\n".join(parts) + "\n</svg>", W, H


# ---- pages -------------------------------------------------------------------
def render_html(s: Session, now: datetime) -> tuple[str, int, int]:
    svg, w, h = render_wide(s, now)
    title = esc(f"Session map · {s.date} · {s.session}")
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link href="{FONT_LINK}" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ background: {PAPER}; }}
    body {{ width: {w}px; color: {INK}; font-family: {FONT_SANS}; }}
    svg {{ display: block; width: {w}px; height: {h}px; }}
  </style>
</head>
<body>
{svg}
</body>
</html>
""", w, h


def render_artifact_html(s: Session, now: datetime) -> str:
    """Page body for the Artifact tool — no doctype/html/head/body (the tool
    wraps it). Two maps, one page: the wide one on desktop, the narrow one
    on phones; each keeps its own prefixed title/desc ids."""
    wide, ww, _ = render_wide(s, now)
    narrow, nw, _ = render_narrow(s, now)
    title = esc(f"Session map · {s.date} · {s.session}")
    return f"""<title>{title}</title>
<link href="{FONT_LINK}" rel="stylesheet">
<style>
  body {{ margin: 0; padding: 24px 16px; background: {PAPER}; color: {INK}; font-family: {FONT_SANS}; }}
  .frame {{ max-width: {ww}px; margin: 0 auto; overflow-x: auto; }}
  .frame svg {{ display: block; height: auto; }}
  .session-map-wide {{ width: 100%; min-width: 720px; }}
  .session-map-narrow {{ display: none; width: 100%; max-width: {nw}px; margin: 0 auto; }}
  @media (max-width: 719px) {{
    .frame {{ overflow-x: visible; }}
    .session-map-wide {{ display: none; }}
    .session-map-narrow {{ display: block; }}
  }}
</style>
<div class="frame">
{wide}
{narrow}
</div>
"""


# ---- PNG via headless Chrome ---------------------------------------------------
CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium",
)


def find_chrome(explicit: str | None = None) -> str | None:
    for cand in ([explicit] if explicit else []) + [os.environ.get("SESSION_DIAGRAM_CHROME", "")] + list(CHROME_CANDIDATES):
        if not cand:
            continue
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        found = shutil.which(cand)
        if found:
            return found
    return None


def render_png(html_path: Path, png_path: Path, w: int, h: int, scale: int, chrome: str,
               timeout: float = 40.0) -> Path | None:
    """Screenshot the page at exactly w×h CSS px. Chrome on macOS keeps running
    after writing the file (its updater child): poll for the PNG, then terminate."""
    profile = tempfile.mkdtemp(prefix="session-diagram-chrome-")
    if png_path.exists():
        png_path.unlink()
    cmd = [chrome, f"--user-data-dir={profile}", "--headless", "--no-first-run", "--disable-gpu",
           "--hide-scrollbars", "--disable-background-networking", "--disable-component-update",
           "--disable-sync", "--disable-default-apps", "--no-default-browser-check", "--disable-extensions",
           f"--force-device-scale-factor={scale}", f"--window-size={w},{h}", "--virtual-time-budget=8000",
           f"--screenshot={png_path}", html_path.resolve().as_uri()]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.insert(1, "--no-sandbox")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + timeout
    last, stable = -1, 0
    try:
        while time.time() < deadline:
            size = png_path.stat().st_size if png_path.exists() else 0
            if size > 0:
                stable = stable + 1 if size == last else 0
                last = size
                if stable >= 2 or proc.poll() is not None:
                    break
            elif proc.poll() is not None:
                break
            time.sleep(0.25)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(profile, ignore_errors=True)
    return png_path if png_path.exists() and png_path.stat().st_size > 0 else None


def photo_scale(requested: int, w: int, h: int) -> int:
    scale = max(1, requested)
    while scale > 1 and scale * (w + h) > TELEGRAM_PHOTO_MAX_SUM:
        scale -= 1
    return scale


def self_check(html_path: Path) -> tuple[bool, str]:
    script = SKILL_DIR / "scripts" / "self_check.py"
    if not script.is_file():
        return True, f"self_check skipped (no {script})"
    r = subprocess.run([sys.executable, str(script), str(html_path)], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


# ---- files + CLI -------------------------------------------------------------
def write_outputs(s: Session, out_dir: Path, now: datetime, check: bool, png: bool, scale: int,
                  chrome: str | None) -> tuple[int, Path, Path | None]:
    out_dir.mkdir(parents=True, exist_ok=True)
    base = s.session
    s.save(out_dir / f"{base}.json")
    page, w, h = render_html(s, now)
    html_path = out_dir / f"{base}.html"
    html_path.write_text(page, encoding="utf-8")
    artifact = out_dir / f"{base}.artifact.html"
    artifact.write_text(render_artifact_html(s, now), encoding="utf-8")
    rc = 0
    if check:
        ok, msg = self_check(artifact)
        print(f"check: {'OK' if ok else 'FAIL — ' + msg}")
        if not ok:
            rc = 2
    png_path: Path | None = None
    if png:
        ch = find_chrome(chrome)
        if not ch:
            print("png: skipped — no Chrome/Chromium found (set SESSION_DIAGRAM_CHROME or --chrome)")
        else:
            png_path = render_png(html_path, out_dir / f"{base}.png", w, h, photo_scale(scale, w, h), ch)
            print(f"png: {png_path}" if png_path else "png: FAILED — Chrome produced no file")
    print(f"artifact: {artifact}")
    return rc, artifact, png_path


def _read_json(text: str, what: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{what}: invalid JSON — {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Session map behind /session-worktree (diagram-design system).")
    ap.add_argument("command", choices=["map", "patch", "show", "render", "sample", "sample-patch"])
    ap.add_argument("--session", help="session id (default: <role>-<id> from the launcher env)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--tree", action="store_true", help="show/map/patch: also print the 🌳 text tree")
    ap.add_argument("--no-check", action="store_true", help="skip diagram-design's self_check.py")
    ap.add_argument("--png", action="store_true", help="also render a PNG with headless Chrome")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--chrome", help="path to a Chrome/Chromium binary")
    ap.add_argument("--send", action="store_true", help="opt-in: Telegram the PNG (or HTML) to the CEO")
    args = ap.parse_args(argv)

    if args.command == "sample":
        print(json.dumps(SAMPLE, ensure_ascii=False, indent=2))
        return 0
    if args.command == "sample-patch":
        print(json.dumps(SAMPLE_PATCH, ensure_ascii=False, indent=2))
        return 0

    now = now_local()
    out_dir = Path(args.out_dir)
    sid = args.session or _session_id_from_env()
    if not sid:
        print("no session id: pass --session or run inside a launched C-level session", file=sys.stderr)
        return 1
    map_path = out_dir / f"{sid}.json"
    try:
        if args.command == "map":
            data = _read_json(sys.stdin.read(), "map")
            s = Session(data, session_id=sid)
            for g in s.goals:                      # first creation: start clocks on doing/blocked items only
                for t in g.tasks:
                    t.stamp(None, now, creation=True)
                for d in g.detours:
                    d.stamp(None, now, creation=True)
                g.stamp(None, now, creation=True)
            s.refresh()
            s.runs = 1
            changes = ["map created"]
        elif args.command == "patch":
            if not map_path.is_file():
                print(f"no map yet for {sid} — run `map` first ({map_path})", file=sys.stderr)
                return 1
            s = Session.load(map_path)
            changes = s.apply_patch(_read_json(sys.stdin.read(), "patch"), now)
            s.runs += 1
        else:
            if not map_path.is_file():
                print(f"no map for {sid} ({map_path})", file=sys.stderr)
                return 1
            s = Session.load(map_path)
            changes = []
    except (OSError, ValueError, TypeError) as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 1

    if args.command == "show":
        print(tree_text(s, now) if args.tree else status_text(s, now))
        print(f"artifact: {out_dir / f'{sid}.artifact.html'}")
        return 0

    if changes and args.command == "patch":
        print("changes: " + " · ".join(changes))
    if args.tree:
        print(tree_text(s, now))
        print("---")
    else:
        print(status_text(s, now))
    rc, artifact, png_path = write_outputs(s, out_dir, now, not args.no_check, args.png, args.scale, args.chrome)

    if args.send:
        sys.path.insert(0, str(ROOT))
        from lib.telegram_out import send_media_to_ceo  # noqa: E402
        c = s.counts()
        caption = (f"🗺 {s.date} · {s.session} — goals {c['goals_done']}/{c['goals']} · "
                   f"tasks {c['tasks_done']}/{c['tasks']} · 🔴 {c['blocked']}\n🎯 {s.entry_problem[:300]}")
        target = png_path or (out_dir / f"{sid}.html")
        res = send_media_to_ceo(str(target), caption)
        print(f"telegram: {'ok' if res.get('ok') else 'FAILED — ' + str(res.get('reason'))} ({target.name})")
        if not res.get("ok"):
            rc = rc or 3
    return rc


if __name__ == "__main__":
    sys.exit(main())
